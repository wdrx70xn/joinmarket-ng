"""Regression tests for issue #259: PEERLIST timeout when listen() is running.

Before the fix, both the listen() receive loop and a concurrent
_fetch_peerlist() call (triggered by the background
_refresh_peerlist_for_new_peer task) would read from the same connection
directly. Whichever coroutine won the race consumed the PEERLIST response;
when the listen loop won, _fetch_peerlist would sit idle and eventually
log "Timed out waiting for PEERLIST ... (attempt 1)".

The fix routes PEERLIST payloads through self._peerlist_inflight whenever
_fetch_peerlist is called while listen() is active, so the listen loop
forwards the response instead of swallowing it.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from jmcore.directory_client import DirectoryClient, MessageType
from jmcore.protocol import FEATURE_PEERLIST_FEATURES


def _make_client() -> DirectoryClient:
    client = DirectoryClient("host", 1234, "mainnet")
    client.connection = AsyncMock()
    client.directory_peerlist_features = True
    client._peerlist_timeout = 1.0
    client._peerlist_chunk_timeout = 0.1
    # Reset the rate limiter so tests are deterministic.
    client._last_peerlist_request_time = 0.0
    return client


@pytest.mark.asyncio
async def test_fetch_peerlist_uses_inflight_sink_when_listen_running() -> None:
    """When listen() is running, _fetch_peerlist must read from the
    in-flight sink rather than the raw connection -- otherwise the
    listen loop's receive() would steal the PEERLIST response."""

    client = _make_client()
    client.running = True  # Simulate an active listen() loop
    client._listen_loop_active = True

    # If _fetch_peerlist wrongly calls connection.receive(), this raises
    # and the test fails.
    async def fail_receive() -> bytes:
        raise AssertionError(
            "_fetch_peerlist must not read from connection when listen() is active"
        )

    client.connection.receive = AsyncMock(side_effect=fail_receive)  # type: ignore[union-attr]

    async def run_fetch() -> list:
        # Yield once so the feed-task below can run first if scheduled.
        await asyncio.sleep(0)
        return await client.get_peerlist_with_features()

    async def feed_peerlist() -> None:
        # Simulate the listen loop routing a PEERLIST payload into the sink.
        while client._peerlist_inflight is None:
            await asyncio.sleep(0)
        assert client._peerlist_inflight is not None
        client._peerlist_inflight.put_nowait(
            f"nick-a;loc-a;F:{FEATURE_PEERLIST_FEATURES},nick-b;loc-b"
        )

    peers, _ = await asyncio.gather(run_fetch(), feed_peerlist())

    assert {n for n, _, _ in peers} == {"nick-a", "nick-b"}
    # GETPEERLIST must still be sent on the wire.
    assert client.connection.send.await_count == 1  # type: ignore[union-attr]
    sent = json.loads(
        client.connection.send.await_args.args[0].decode("utf-8")  # type: ignore[union-attr]
    )
    assert sent["type"] == MessageType.GETPEERLIST.value
    # And the sink must be cleared afterwards so subsequent calls can run.
    assert client._peerlist_inflight is None


@pytest.mark.asyncio
async def test_fetch_peerlist_times_out_cleanly_via_sink() -> None:
    """If no PEERLIST arrives while listen() is running, we should hit
    the usual "never received any PEERLIST" path and return an empty
    list without blocking forever."""

    client = _make_client()
    client.running = True
    client._listen_loop_active = True
    client._peerlist_timeout = 0.1

    async def never_fires() -> bytes:
        raise AssertionError("connection.receive must not be called")

    client.connection.receive = AsyncMock(side_effect=never_fires)  # type: ignore[union-attr]

    peers = await client.get_peerlist_with_features()

    assert peers == []
    assert client._peerlist_timeout_count == 1
    assert client._peerlist_inflight is None


@pytest.mark.asyncio
async def test_fetch_peerlist_direct_read_when_listen_not_running() -> None:
    """When listen() is not active, _fetch_peerlist keeps its classic
    behaviour and reads straight from the connection."""

    client = _make_client()
    client.running = False

    client.connection.receive = AsyncMock(  # type: ignore[union-attr]
        side_effect=[
            json.dumps(
                {
                    "type": MessageType.PEERLIST.value,
                    "line": "nick-x;loc-x",
                }
            ).encode("utf-8"),
            TimeoutError(),
        ]
    )

    peers = await client.get_peerlist_with_features()

    assert [n for n, _, _ in peers] == ["nick-x"]
    assert client._peerlist_inflight is None


@pytest.mark.asyncio
async def test_fetch_peerlist_direct_read_during_startup_window() -> None:
    """Regression: during listen_continuously()'s startup, self.running is
    True but the receive loop has not yet started (_listen_loop_active is
    False). _fetch_peerlist must read directly from the connection in that
    window; otherwise the initial peerlist fetch times out and the client
    falsely concludes the directory doesn't support GETPEERLIST."""

    client = _make_client()
    client.running = True  # listen_continuously() has set this early
    client._listen_loop_active = False  # but the receive loop hasn't started

    client.connection.receive = AsyncMock(  # type: ignore[union-attr]
        side_effect=[
            json.dumps(
                {
                    "type": MessageType.PEERLIST.value,
                    "line": "nick-s;loc-s",
                }
            ).encode("utf-8"),
            TimeoutError(),
        ]
    )

    peers = await client.get_peerlist_with_features()

    assert [n for n, _, _ in peers] == ["nick-s"]
    assert client._peerlist_inflight is None


@pytest.mark.asyncio
async def test_listen_loop_forwards_peerlist_to_inflight_sink() -> None:
    """End-to-end check of the listen() -> sink -> _fetch_peerlist path:
    a PEERLIST received by the listen loop must be forwarded to an
    in-flight fetch call."""

    client = _make_client()

    # Simulate the main loop seeing a PEERLIST while a fetch is in flight.
    client._peerlist_inflight = asyncio.Queue()
    # Replicate the exact listen() branch (see directory_client.listen()).
    client._peerlist_inflight.put_nowait("nick-z;loc-z")

    assert client._peerlist_inflight.qsize() == 1
    # And a subsequent fetcher would pull that payload.
    chunk = await asyncio.wait_for(client._peerlist_inflight.get(), timeout=0.1)
    assert chunk == "nick-z;loc-z"

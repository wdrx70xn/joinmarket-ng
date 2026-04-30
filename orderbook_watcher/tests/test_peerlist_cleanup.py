"""
Tests for the per-directory peerlist cleanup behaviour in
OrderbookAggregator._periodic_peerlist_refresh().

The watcher trusts each directory's view: an offer announced through
directory D is dropped from that directory's cache as soon as D no longer
lists the maker in its peerlist (whether via an explicit ;D broadcast or
a refresh that omits the nick). Cleanup is purely per-directory; offers
held by other directories are unaffected.

Reference implementation directories (no GETPEERLIST support) fall back
to age-based pruning via cleanup_stale_offers().
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from jmcore.directory_client import DirectoryClient, OfferWithTimestamp
from jmcore.models import Offer, OfferType

import orderbook_watcher.aggregator as agg_mod
from orderbook_watcher.aggregator import OrderbookAggregator


def _make_offer(nick: str, oid: int = 0) -> Offer:
    return Offer(
        counterparty=nick,
        oid=oid,
        ordertype=OfferType("sw0reloffer"),
        minsize=100_000,
        maxsize=10_000_000,
        txfee=0,
        cjfee="0.001",
        fidelity_bond_value=0,
    )


def _make_client(
    *,
    nicks_with_offers: list[str],
    active_nicks: list[str],
    peerlist_supported: bool = True,
    refresh_raises: bool = False,
) -> MagicMock:
    """Build a MagicMock DirectoryClient with prescribed state."""
    client = MagicMock(spec=DirectoryClient)
    client.offers = {}
    for nick in nicks_with_offers:
        client.offers[(nick, 0)] = OfferWithTimestamp(
            offer=_make_offer(nick),
            received_at=time.time(),
            bond_utxo_key=None,
        )
    client._active_peers = {nick: f"{nick}.onion:5222" for nick in active_nicks}
    client.peer_features = {nick: {} for nick in active_nicks}
    client._peerlist_supported = peerlist_supported

    if refresh_raises:
        client.get_peerlist_with_features = AsyncMock(side_effect=RuntimeError("boom"))
    else:
        client.get_peerlist_with_features = AsyncMock(return_value=[])

    client.get_active_nicks = MagicMock(side_effect=lambda: set(client._active_peers.keys()))

    def _remove(nick: str) -> int:
        keys = [k for k in list(client.offers.keys()) if k[0] == nick]
        for k in keys:
            client.offers.pop(k, None)
        return len(keys)

    client.remove_offers_for_nick = MagicMock(side_effect=_remove)

    def _cleanup_stale(max_age_seconds: float) -> int:  # noqa: ARG001
        # In tests we never put aged offers; default returns zero.
        return 0

    client.cleanup_stale_offers = MagicMock(side_effect=_cleanup_stale)

    return client


def _build_aggregator() -> OrderbookAggregator:
    return OrderbookAggregator(
        directory_nodes=[],
        network="regtest",
        mempool_api_url="",
    )


async def _run_one_refresh_iteration(agg: OrderbookAggregator) -> None:
    """Run _periodic_peerlist_refresh just long enough to perform one pass."""
    # Patch sleep so the task ticks immediately and exits via cancel after one pass.
    original_sleep = asyncio.sleep

    sleep_calls: list[float] = []

    async def fast_sleep(delay: float) -> None:
        sleep_calls.append(delay)
        # First sleep is the 120s startup wait; second sleep is the 300s loop
        # interval. Cancel after the loop sleep to give one iteration.
        if len(sleep_calls) >= 2:
            raise asyncio.CancelledError
        await original_sleep(0)

    # Replace _check_makers_without_features with a no-op to isolate cleanup
    # behaviour from feature-discovery side effects.
    agg._check_makers_without_features = AsyncMock()  # type: ignore[method-assign]

    original = agg_mod.asyncio.sleep
    agg_mod.asyncio.sleep = fast_sleep  # type: ignore[assignment]
    try:
        # The task catches CancelledError internally and returns normally.
        await agg._periodic_peerlist_refresh()
    finally:
        agg_mod.asyncio.sleep = original  # type: ignore[assignment]


class TestPerDirectoryPeerlistCleanup:
    @pytest.mark.asyncio
    async def test_removes_offers_for_nicks_not_in_directory_peerlist(self) -> None:
        """Offers from nicks the directory no longer reports must be dropped."""
        client = _make_client(
            nicks_with_offers=["alice", "bob", "carol"],
            active_nicks=["alice", "carol"],  # bob disappeared
            peerlist_supported=True,
        )
        agg = _build_aggregator()
        agg.clients = {"node1:5222": client}

        await _run_one_refresh_iteration(agg)

        client.remove_offers_for_nick.assert_called_once_with("bob")
        assert ("bob", 0) not in client.offers
        assert ("alice", 0) in client.offers
        assert ("carol", 0) in client.offers

    @pytest.mark.asyncio
    async def test_per_directory_isolation(self) -> None:
        """A nick missing from one directory must NOT be removed from another."""
        # Same maker "shared" on two directories. On node1 it disconnected;
        # node2 still lists it. node1 should drop it, node2 should keep it.
        node1 = _make_client(
            nicks_with_offers=["shared", "alice"],
            active_nicks=["alice"],
            peerlist_supported=True,
        )
        node2 = _make_client(
            nicks_with_offers=["shared", "alice"],
            active_nicks=["shared", "alice"],
            peerlist_supported=True,
        )
        agg = _build_aggregator()
        agg.clients = {"node1:5222": node1, "node2:5222": node2}

        await _run_one_refresh_iteration(agg)

        node1.remove_offers_for_nick.assert_called_once_with("shared")
        assert ("shared", 0) not in node1.offers
        assert ("shared", 0) in node2.offers
        # node2 had nothing to remove
        node2.remove_offers_for_nick.assert_not_called()

    @pytest.mark.asyncio
    async def test_refresh_failure_skips_cleanup_for_that_directory(self) -> None:
        """If GETPEERLIST fails for a directory we keep its current state."""
        client = _make_client(
            nicks_with_offers=["alice", "bob"],
            active_nicks=["alice"],
            peerlist_supported=True,
            refresh_raises=True,
        )
        agg = _build_aggregator()
        agg.clients = {"node1:5222": client}

        await _run_one_refresh_iteration(agg)

        # Refresh failed -> we don't trust the active list -> no removals.
        client.remove_offers_for_nick.assert_not_called()
        assert ("alice", 0) in client.offers
        assert ("bob", 0) in client.offers

    @pytest.mark.asyncio
    async def test_directory_without_getpeerlist_falls_back_to_stale_cleanup(self) -> None:
        """Reference-impl directories use age-based cleanup, not peerlist diff."""
        client = _make_client(
            nicks_with_offers=["alice", "bob"],
            active_nicks=[],  # none reported
            peerlist_supported=False,
        )
        agg = _build_aggregator()
        agg.clients = {"node1:5222": client}

        await _run_one_refresh_iteration(agg)

        # Must NOT call remove_offers_for_nick (we don't have a trusted list).
        client.remove_offers_for_nick.assert_not_called()
        # Must call cleanup_stale_offers as the fallback.
        client.cleanup_stale_offers.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_op_when_directory_state_matches(self) -> None:
        """When peerlist matches the offer cache, nothing is removed."""
        client = _make_client(
            nicks_with_offers=["alice", "bob"],
            active_nicks=["alice", "bob"],
            peerlist_supported=True,
        )
        agg = _build_aggregator()
        agg.clients = {"node1:5222": client}

        await _run_one_refresh_iteration(agg)

        client.remove_offers_for_nick.assert_not_called()
        assert ("alice", 0) in client.offers
        assert ("bob", 0) in client.offers

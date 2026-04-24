"""Tests for the /api/v1/logs endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from loguru import logger

from jmwalletd.log_buffer import get_log_buffer, install_log_sink


@pytest.fixture
def authed_client(app_with_wallet: TestClient, auth_token: str) -> tuple[TestClient, str]:
    return app_with_wallet, auth_token


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestGetLogs:
    def test_returns_401_without_auth(self, app_with_wallet: TestClient) -> None:
        response = app_with_wallet.get("/api/v1/logs")
        assert response.status_code == 401

    def test_returns_plain_text(self, authed_client: tuple[TestClient, str]) -> None:
        client, token = authed_client
        response = client.get("/api/v1/logs", headers=_auth_headers(token))
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")

    def test_captures_logged_messages(
        self,
        authed_client: tuple[TestClient, str],
    ) -> None:
        client, token = authed_client
        # Reset and (re)install the sink to ensure a clean buffer state after
        # other tests that may have called ``logger.remove()``.
        buffer = get_log_buffer()
        buffer.clear()
        install_log_sink()

        logger.info("probe-marker-12345")

        response = client.get("/api/v1/logs", headers=_auth_headers(token))
        assert response.status_code == 200
        assert "probe-marker-12345" in response.text


class TestLogRingBuffer:
    def test_appends_and_returns_text(self) -> None:
        from jmwalletd.log_buffer import LogRingBuffer

        buf = LogRingBuffer(max_lines=3, max_bytes=1_000)
        buf.append("one\n")
        buf.append("two\n")
        buf.append("three\n")
        assert buf.text() == "one\ntwo\nthree\n"

    def test_evicts_oldest_when_line_cap_reached(self) -> None:
        from jmwalletd.log_buffer import LogRingBuffer

        buf = LogRingBuffer(max_lines=2, max_bytes=1_000)
        buf.append("one\n")
        buf.append("two\n")
        buf.append("three\n")
        assert buf.text() == "two\nthree\n"

    def test_evicts_when_byte_cap_reached(self) -> None:
        from jmwalletd.log_buffer import LogRingBuffer

        buf = LogRingBuffer(max_lines=100, max_bytes=8)
        buf.append("aaaa\n")
        buf.append("bbbb\n")
        # First entry (5 bytes) evicted because adding the second (5 bytes)
        # would push total (10) above the 8-byte cap.
        assert buf.text() == "bbbb\n"

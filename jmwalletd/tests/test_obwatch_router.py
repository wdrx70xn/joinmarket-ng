"""Tests for orderbook watcher proxy endpoints."""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from jmwalletd.routers.obwatch import _get_obwatch_url
from jmwalletd.state import DaemonState


@pytest.fixture
def client(app: TestClient) -> TestClient:
    return app


class TestObWatch:
    def test_get_obwatch_url_prefers_env(self) -> None:
        state = cast(DaemonState, object())
        with patch.dict("os.environ", {"OBWATCH_URL": "http://127.0.0.1:39123"}, clear=False):
            assert _get_obwatch_url(state=state) == "http://127.0.0.1:39123"

    def test_get_obwatch_url_from_settings(self) -> None:
        state = cast(DaemonState, object())
        mock_settings = AsyncMock()
        mock_settings.orderbook_watcher.http_host = "127.0.0.1"
        mock_settings.orderbook_watcher.http_port = 39123

        with (
            patch.dict("os.environ", {}, clear=True),
            patch("jmcore.settings.get_settings", return_value=mock_settings),
        ):
            assert _get_obwatch_url(state=state) == "http://127.0.0.1:39123"

    def test_get_obwatch_url_maps_bind_all_to_loopback(self) -> None:
        state = cast(DaemonState, object())
        mock_settings = AsyncMock()
        mock_settings.orderbook_watcher.http_host = "0.0.0.0"
        mock_settings.orderbook_watcher.http_port = 39123

        with (
            patch.dict("os.environ", {}, clear=True),
            patch("jmcore.settings.get_settings", return_value=mock_settings),
        ):
            assert _get_obwatch_url(state=state) == "http://127.0.0.1:39123"

    @patch("jmwalletd.routers.obwatch.aiohttp.ClientSession.get")
    def test_get_orderbook(self, mock_get: AsyncMock, client: TestClient) -> None:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = {"offers": [], "fidelitybonds": []}
        mock_get.return_value.__aenter__.return_value = mock_resp

        resp = client.get("/api/v1/obwatch/orderbook.json")
        assert resp.status_code == 200
        assert resp.json() == {"offers": [], "fidelitybonds": []}

    @patch("jmwalletd.routers.obwatch.aiohttp.ClientSession.get")
    def test_get_orderbook_error(self, mock_get: AsyncMock, client: TestClient) -> None:
        mock_get.side_effect = Exception("Connection error")

        resp = client.get("/api/v1/obwatch/orderbook.json")
        assert resp.status_code == 502
        assert resp.json() == {"offers": [], "fidelitybonds": []}

    @patch("jmwalletd.routers.obwatch.aiohttp.ClientSession.get")
    def test_refresh_orderbook(self, mock_get: AsyncMock, client: TestClient) -> None:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = {"offers": []}
        mock_get.return_value.__aenter__.return_value = mock_resp

        resp = client.get("/api/v1/obwatch/refreshorderbook")
        assert resp.status_code == 200

    @patch("jmwalletd.routers.obwatch.aiohttp.ClientSession.get")
    def test_refresh_orderbook_post(self, mock_get: AsyncMock, client: TestClient) -> None:
        """JAM calls POST /obwatch/refreshorderbook; ensure it is accepted."""
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = {"offers": [], "fidelitybonds": []}
        mock_get.return_value.__aenter__.return_value = mock_resp

        resp = client.post("/api/v1/obwatch/refreshorderbook")
        assert resp.status_code == 200

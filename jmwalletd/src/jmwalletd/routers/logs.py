"""Log retrieval endpoint.

Serves the most recent log output captured by the ``log_buffer`` sink as plain
text. Used by jam's Logs page. The endpoint requires authentication because
logs can contain wallet/activity metadata.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from jmwalletd.deps import require_auth
from jmwalletd.log_buffer import get_log_buffer

router = APIRouter()


@router.get("/logs", operation_id="getlogs", response_class=PlainTextResponse)
async def get_logs(_auth: dict[str, Any] = Depends(require_auth)) -> PlainTextResponse:
    """Return the recent in-memory log buffer as plain text."""
    return PlainTextResponse(content=get_log_buffer().text())

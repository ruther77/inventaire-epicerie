from __future__ import annotations

from typing import Protocol


class BaseTransport:
    """Minimal interface compatible with Starlette's expectations."""

    def handle_request(self, request: "Request"):
        raise NotImplementedError


class AsyncBaseTransport(Protocol):  # pragma: no cover - unused placeholder
    async def handle_async_request(self, request: "Request"):
        ...

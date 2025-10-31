from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping
from urllib.parse import urljoin

from . import _types
from ._models import Headers, Request, Response, URL
from ._transport import BaseTransport


@dataclass(frozen=True)
class UseClientDefault:
    """Sentinel mirroring the public constant in real httpx."""


USE_CLIENT_DEFAULT = UseClientDefault()


class Client:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        headers: Mapping[str, str] | None = None,
        transport: BaseTransport | None = None,
        follow_redirects: bool = True,
        cookies: _types.CookieTypes = None,
        timeout: _types.TimeoutTypes = None,
    ) -> None:
        self.base_url = base_url
        self._transport = transport
        self.follow_redirects = follow_redirects
        self.cookies = cookies
        self.timeout = timeout
        self.headers = Headers(headers or {})
        self._closed = False

    # Compatibility helpers -------------------------------------------------
    def _merge_url(self, url: _types.URLTypes) -> URL:
        if isinstance(url, URL):
            return url
        if isinstance(url, bytes):
            url = url.decode()
        if self.base_url:
            absolute = urljoin(self.base_url, str(url))
        else:
            absolute = str(url)
        return URL.from_string(absolute)

    def build_request(
        self,
        method: str,
        url: _types.URLTypes,
        *,
        content: _types.RequestContent | None = None,
        data: _types.RequestData = None,
        files: _types.RequestFiles = None,
        json: Any = None,
        params: _types.QueryParamTypes = None,
        headers: _types.HeaderTypes = None,
        cookies: _types.CookieTypes = None,
    ) -> Request:
        base_headers = Headers(self.headers.multi_items())
        if headers:
            base_headers.update(headers)  # type: ignore[arg-type]
        merged_url = self._merge_url(url)
        return Request(
            method,
            merged_url,
            content=content,
            data=data,
            files=files,
            json_data=json,
            params=params,
            headers=base_headers,
            cookies=cookies or self.cookies,
        )

    def send(self, request: Request, *, stream: bool = False) -> Response:
        if self._transport is None:
            raise RuntimeError("A transport instance is required to send requests")
        response = self._transport.handle_request(request)
        return response

    # Public request API ----------------------------------------------------
    def request(
        self,
        method: str,
        url: _types.URLTypes,
        *,
        content: _types.RequestContent | None = None,
        data: _types.RequestData = None,
        files: _types.RequestFiles = None,
        json: Any = None,
        params: _types.QueryParamTypes = None,
        headers: _types.HeaderTypes = None,
        cookies: _types.CookieTypes = None,
        auth: _types.AuthTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
        timeout: _types.TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        extensions: Dict[str, Any] | None = None,
    ) -> Response:
        request = self.build_request(
            method,
            url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
        )
        return self.send(request)

    # Convenience HTTP verb helpers ----------------------------------------
    def get(self, url: _types.URLTypes, **kwargs) -> Response:
        return self.request("GET", url, **kwargs)

    def options(self, url: _types.URLTypes, **kwargs) -> Response:
        return self.request("OPTIONS", url, **kwargs)

    def head(self, url: _types.URLTypes, **kwargs) -> Response:
        return self.request("HEAD", url, **kwargs)

    def post(self, url: _types.URLTypes, **kwargs) -> Response:
        return self.request("POST", url, **kwargs)

    def put(self, url: _types.URLTypes, **kwargs) -> Response:
        return self.request("PUT", url, **kwargs)

    def patch(self, url: _types.URLTypes, **kwargs) -> Response:
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: _types.URLTypes, **kwargs) -> Response:
        return self.request("DELETE", url, **kwargs)

    def close(self) -> None:
        self._closed = True

    def __enter__(self) -> "Client":  # pragma: no cover - standard context mgr behaviour
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - trivial
        self.close()


__all__ = [
    "Client",
    "UseClientDefault",
    "USE_CLIENT_DEFAULT",
]

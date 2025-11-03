from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple, Union
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit

from . import _types


class Headers:
    """Lightweight case-insensitive headers container."""

    def __init__(self, data: Union[None, Dict[str, str], Iterable[Tuple[str, str]]] = None):
        self._items: List[Tuple[str, str]] = []
        if data:
            if isinstance(data, dict):
                items = data.items()
            else:
                items = data
            for key, value in items:
                self[key] = value

    def __setitem__(self, key: str, value: str) -> None:
        key_str = str(key)
        value_str = str(value)
        for idx, (existing_key, _) in enumerate(self._items):
            if existing_key.lower() == key_str.lower():
                self._items[idx] = (existing_key, value_str)
                break
        else:
            self._items.append((key_str, value_str))

    def add(self, key: str, value: str) -> None:
        self._items.append((str(key), str(value)))

    def get(self, key: str, default: Union[str, None] = None) -> Union[str, None]:
        key_lower = key.lower()
        for existing_key, value in reversed(self._items):
            if existing_key.lower() == key_lower:
                return value
        return default

    def items(self) -> List[Tuple[str, str]]:
        return list(self._items)

    def multi_items(self) -> List[Tuple[str, str]]:
        return list(self._items)

    def update(self, other: Union[Dict[str, str], Iterable[Tuple[str, str]]]) -> None:
        if isinstance(other, dict):
            iterator = other.items()
        else:
            iterator = other
        for key, value in iterator:
            self[key] = value

    def __iter__(self):
        return iter(self._items)

    def __contains__(self, key: str) -> bool:
        key_lower = key.lower()
        return any(existing_key.lower() == key_lower for existing_key, _ in self._items)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"Headers({self._items!r})"


@dataclass
class URL:
    scheme: str
    netloc: bytes
    path: str
    raw_path: bytes
    query: bytes

    @classmethod
    def from_string(cls, value: str) -> "URL":
        parsed = urlsplit(value)
        scheme = parsed.scheme or "http"
        netloc_str = parsed.netloc or ""
        path = parsed.path or "/"
        query = parsed.query
        raw_path = path.encode("ascii", errors="ignore")
        if query:
            raw_path = raw_path + b"?" + query.encode("ascii", errors="ignore")
        return cls(
            scheme=scheme,
            netloc=netloc_str.encode("ascii", errors="ignore"),
            path=path,
            raw_path=raw_path,
            query=query.encode("ascii", errors="ignore"),
        )

    def join(self, other: _types.URLTypes) -> "URL":
        if isinstance(other, bytes):
            other = other.decode()
        if isinstance(other, str):
            combined = urljoin(self.as_string(), other)
        else:
            combined = self.as_string()
        return URL.from_string(combined)

    def as_string(self) -> str:
        return urlunsplit((self.scheme, self.netloc.decode("ascii"), self.path, self.query.decode("ascii"), ""))

    def __str__(self) -> str:  # pragma: no cover
        return self.as_string()


class ByteStream:
    def __init__(self, data: Union[bytes, bytearray, memoryview]):
        self._data = bytes(data)

    def read(self) -> bytes:
        return self._data


class Request:
    def __init__(
        self,
        method: str,
        url: Union[str, URL],
        *,
        content: _types.RequestContent | None = None,
        data: _types.RequestData = None,
        files: _types.RequestFiles = None,
        json_data=None,
        params: _types.QueryParamTypes = None,
        headers: Union[Headers, Dict[str, str], Iterable[Tuple[str, str]], None] = None,
        cookies: _types.CookieTypes = None,
    ) -> None:
        if isinstance(url, URL):
            url_obj = url
        else:
            if isinstance(url, bytes):
                url = url.decode()
            url_obj = URL.from_string(str(url))
        if params:
            if isinstance(params, (dict, list, tuple)):
                query_string = urlencode(params, doseq=True)
            else:
                query_string = str(params)
            separator = "&" if url_obj.query else ""
            existing = url_obj.query.decode("ascii")
            combined_query = (existing + separator + query_string).strip("&")
            base = url_obj.as_string().split("?")[0]
            url_obj = URL.from_string(base + ("?" + combined_query if combined_query else ""))
        self.method = method.upper()
        self.url = url_obj
        body, inferred_headers = self._prepare_body(content, data, files, json_data)
        self._body = body
        if headers is None:
            headers_obj = Headers()
        elif isinstance(headers, Headers):
            headers_obj = Headers(headers.multi_items())
        else:
            headers_obj = Headers(headers)
        if inferred_headers:
            headers_obj.update(inferred_headers)
        if self._body is not None and headers_obj.get("content-length") is None:
            headers_obj["content-length"] = str(len(self._body))
        self.headers = headers_obj
        self.cookies = cookies

    def _prepare_body(self, content, data, files, json_data):
        if content is not None:
            if isinstance(content, str):
                return content.encode("utf-8"), {"content-type": "text/plain; charset=utf-8"}
            if isinstance(content, (bytes, bytearray, memoryview)):
                return bytes(content), {}
            raise TypeError("Unsupported content type")
        if json_data is not None:
            body = json.dumps(json_data).encode("utf-8")
            return body, {"content-type": "application/json"}
        if data is not None:
            if isinstance(data, (dict, list, tuple)):
                body = urlencode(data, doseq=True).encode("utf-8")
            elif isinstance(data, (bytes, bytearray, memoryview)):
                body = bytes(data)
            else:
                body = str(data).encode("utf-8")
            return body, {"content-type": "application/x-www-form-urlencoded"}
        return b"", {}

    def read(self):
        return self._body


class Response:
    def __init__(
        self,
        status_code: int,
        *,
        headers: Iterable[Tuple[str, str]] | Dict[str, str] | None = None,
        stream: ByteStream | None = None,
        content: Union[bytes, bytearray, memoryview, str, None] = None,
        request: Request | None = None,
    ) -> None:
        self.status_code = status_code
        self.headers = Headers(headers or {})
        self._stream = stream
        if content is None and stream is not None:
            self._content: bytes | None = None
        elif content is None:
            self._content = b""
        elif isinstance(content, str):
            self._content = content.encode("utf-8")
        else:
            self._content = bytes(content)
        self.request = request

    def read(self) -> bytes:
        if self._content is None and self._stream is not None:
            self._content = self._stream.read()
        return self._content or b""

    @property
    def content(self) -> bytes:
        return self.read()

    @property
    def text(self) -> str:
        return self.read().decode("utf-8")

    def json(self):
        data = self.read()
        if not data:
            return None
        return json.loads(data.decode("utf-8"))

    def __repr__(self) -> str:  # pragma: no cover
        return f"Response(status_code={self.status_code!r})"

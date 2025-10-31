from __future__ import annotations

from typing import Any, Iterable, Mapping, MutableMapping, Sequence, Tuple, Union

URLTypes = Union[str, bytes]
RequestContent = Union[bytes, bytearray, memoryview, str]
RequestData = Union[Mapping[str, Any], Sequence[Tuple[str, Any]], str, bytes, None]
RequestFiles = Any
QueryParamTypes = Union[str, bytes, MutableMapping[str, Any], Sequence[Tuple[str, Any]], None]
HeaderTypes = Union[Mapping[str, str], Sequence[Tuple[str, str]], None]
CookieTypes = Any
AuthTypes = Any
TimeoutTypes = Any
ProxiesTypes = Any
CertTypes = Any
VerifyTypes = Any

__all__ = [
    "URLTypes",
    "RequestContent",
    "RequestData",
    "RequestFiles",
    "QueryParamTypes",
    "HeaderTypes",
    "CookieTypes",
    "AuthTypes",
    "TimeoutTypes",
    "ProxiesTypes",
    "CertTypes",
    "VerifyTypes",
]

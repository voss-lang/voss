"""Loopback memory API client; callers must reuse idempotency keys for retries."""

from __future__ import annotations

import json
import math
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from ipaddress import ip_address
from typing import Any, Mapping


DEFAULT_TIMEOUT_SECONDS = 5.0
MAX_TIMEOUT_SECONDS = 30.0
MAX_RESPONSE_BYTES = 8 * 1024 * 1024

_PROJECT_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_IDEMPOTENCY_KEY = re.compile(r"^[\x21-\x7e]{1,128}$")
_KINDS = frozenset({"note", "convention", "decision"})
_REDIRECT_STATUSES = frozenset(range(300, 400))


class MemoryApiError(RuntimeError):
    """An error returned by, or raised while calling, the memory service."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        code: str | None = None,
    ) -> None:
        self.status = status
        self.code = code
        super().__init__(message)


class MemoryApiConfigurationError(MemoryApiError):
    """The local client configuration cannot safely issue a request."""


class MemoryApiUnavailableError(MemoryApiError):
    """The local service could not be reached within the request bounds."""


class MemoryApiRedirectError(MemoryApiError):
    """The service attempted a redirect, which this client never follows."""


@dataclass(frozen=True)
class MemoryApiResponse:
    """Minimal response seam used by tests and custom local transports."""

    status: int
    body: bytes

    def getcode(self) -> int:
        return self.status

    def read(self, amount: int = -1) -> bytes:
        if amount < 0:
            return self.body
        return self.body[:amount]

    def close(self) -> None:
        return None


def _validate_base_url(base_url: str) -> str:
    if not isinstance(base_url, str) or not base_url.strip():
        raise MemoryApiConfigurationError("memory API URL is required")

    raw = base_url.strip()
    try:
        parsed = urllib.parse.urlsplit(raw)
    except ValueError as exc:
        raise MemoryApiConfigurationError("invalid memory API URL") from exc

    if parsed.scheme.lower() not in {"http", "https"}:
        raise MemoryApiConfigurationError("memory API URL must use HTTP or HTTPS")
    if not parsed.hostname:
        raise MemoryApiConfigurationError("memory API URL must include a host")
    if parsed.username is not None or parsed.password is not None:
        raise MemoryApiConfigurationError("memory API URL must not contain credentials")
    if parsed.query or parsed.fragment:
        raise MemoryApiConfigurationError("memory API URL must not contain query or fragment data")
    try:
        parsed.port
    except ValueError as exc:
        raise MemoryApiConfigurationError("memory API URL has an invalid port") from exc
    if parsed.path.rstrip("/"):
        raise MemoryApiConfigurationError("memory API URL must point at the service root")

    host = parsed.hostname.lower().rstrip(".")
    is_loopback_name = host == "localhost"
    if not is_loopback_name:
        try:
            is_loopback_name = ip_address(host).is_loopback
        except ValueError:
            is_loopback_name = False
    if not is_loopback_name:
        raise MemoryApiConfigurationError("memory API URL must target a loopback host")

    return urllib.parse.urlunsplit(
        (parsed.scheme.lower(), parsed.netloc, "", "", "")
    )


def _validate_project_id(project_id: str) -> str:
    if not isinstance(project_id, str) or not _PROJECT_ID.fullmatch(project_id):
        raise ValueError("project id must be 1-64 ASCII letters, digits, underscore, or hyphen")
    return project_id


def _validate_kind(kind: str) -> str:
    if kind not in _KINDS:
        raise ValueError("memory kind must be note, convention, or decision")
    return kind


def _validate_idempotency_key(key: str) -> str:
    if not isinstance(key, str) or not _IDEMPOTENCY_KEY.fullmatch(key):
        raise ValueError("idempotency key must contain 1-128 visible ASCII characters")
    return key


def _validate_timeout(timeout: float) -> float:
    try:
        value = float(timeout)
    except (TypeError, ValueError) as exc:
        raise MemoryApiConfigurationError("memory API timeout must be finite and positive") from exc
    if not math.isfinite(value) or value <= 0 or value > MAX_TIMEOUT_SECONDS:
        raise MemoryApiConfigurationError(
            f"memory API timeout must be between 0 and {MAX_TIMEOUT_SECONDS:g} seconds"
        )
    return value


def _safe_error_message(message: str, token: str | None) -> str:
    text = str(message).replace("\r", " ").replace("\n", " ").strip()
    if token:
        text = text.replace(token, "<redacted>")
    # Redact transformed bearer values as well as the configured token.
    text = re.sub(r"(?i)bearer\s+[^\s,;]+", "Bearer <redacted>", text)
    return text[:512] or "memory API request failed"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class MemoryApiClient:
    def __init__(
        self,
        base_url: str,
        token: str | None = None,
        *,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        opener: Any | None = None,
    ) -> None:
        self.base_url = _validate_base_url(base_url)
        if token is not None and not isinstance(token, str):
            raise MemoryApiConfigurationError("memory API token must be a string")
        if token is not None and ("\r" in token or "\n" in token):
            raise MemoryApiConfigurationError("memory API token contains invalid header characters")
        self.token = token if token and token.strip() else None
        self.timeout = _validate_timeout(timeout)
        self._opener = opener or urllib.request.build_opener(
            _NoRedirect(), urllib.request.ProxyHandler({})
        )

    @classmethod
    def from_env(
        cls,
        *,
        base_url: str | None = None,
        token: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        opener: Any | None = None,
        require_token: bool = True,
    ) -> "MemoryApiClient":
        url = base_url if base_url is not None else os.environ.get("VOSS_MEMORY_API_URL")
        configured_token = token if token is not None else os.environ.get("VOSS_MEMORY_API_TOKEN")
        client = cls(
            url or "",
            configured_token,
            timeout=timeout,
            opener=opener,
        )
        if require_token and not client.token:
            raise MemoryApiConfigurationError("VOSS_MEMORY_API_TOKEN is required for memory API access")
        return client

    def __repr__(self) -> str:
        return (
            f"MemoryApiClient(base_url={self.base_url!r}, "
            f"token={'<redacted>' if self.token else '<missing>'!r}, "
            f"timeout={self.timeout!r})"
        )

    __str__ = __repr__

    @staticmethod
    def validate_project_id(project_id: str) -> str:
        return _validate_project_id(project_id)

    def health(self) -> dict[str, Any]:
        return self._request_json("GET", "/v1/health", auth=False, expected=(200,))

    def register_project(self, project_id: str, *, name: str | None = None) -> dict[str, Any]:
        project_id = _validate_project_id(project_id)
        payload: dict[str, Any] = {"id": project_id}
        if name is not None:
            payload["name"] = name
        return self._data_object(
            self._request_json("POST", "/v1/projects", payload=payload, expected=(200, 201))
        )

    def create_memory(
        self,
        project_id: str,
        kind: str,
        body: str,
        *,
        provenance: Mapping[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        project_id = _validate_project_id(project_id)
        kind = _validate_kind(kind)
        if not isinstance(body, str) or not body.strip():
            raise ValueError("memory body must be a nonempty string")
        if len(body.encode("utf-8")) > 65536:
            raise ValueError("memory body must be at most 65536 UTF-8 bytes")
        key = _validate_idempotency_key(
            uuid.uuid4().hex if idempotency_key is None else idempotency_key
        )
        payload: dict[str, Any] = {"kind": kind, "body": body}
        if provenance is not None:
            if not isinstance(provenance, Mapping):
                raise ValueError("memory provenance must be an object")
            payload["provenance"] = dict(provenance)
        return self._data_object(
            self._request_json(
                "POST",
                f"/v1/projects/{self._segment(project_id)}/memories",
                payload=payload,
                headers={"Idempotency-Key": key},
                expected=(201,),
            )
        )

    def list_memories(
        self,
        project_id: str,
        *,
        kind: str | None = None,
        pinned: bool | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        project_id = _validate_project_id(project_id)
        if kind is not None:
            kind = _validate_kind(kind)
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
            raise ValueError("memory list limit must be between 1 and 100")
        params: dict[str, str] = {"limit": str(limit)}
        if kind is not None:
            params["kind"] = kind
        if pinned is not None:
            params["pinned"] = "true" if pinned else "false"
        if cursor is not None:
            params["cursor"] = cursor
        path = f"/v1/projects/{self._segment(project_id)}/memories"
        return self._request_json("GET", path, params=params, expected=(200,))

    def get_memory(self, project_id: str, memory_id: str) -> dict[str, Any]:
        project_id = _validate_project_id(project_id)
        if not isinstance(memory_id, str) or not memory_id:
            raise ValueError("memory id is required")
        path = (
            f"/v1/projects/{self._segment(project_id)}/memories/"
            f"{self._segment(memory_id)}"
        )
        return self._data_object(self._request_json("GET", path, expected=(200,)))

    def search(
        self,
        project_id: str,
        query: str,
        *,
        kinds: list[str] | tuple[str, ...] | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        project_id = _validate_project_id(project_id)
        if not isinstance(query, str) or not query.strip():
            raise ValueError("memory search query must be nonempty")
        if not isinstance(top_k, int) or isinstance(top_k, bool) or not 1 <= top_k <= 50:
            raise ValueError("memory search top_k must be between 1 and 50")
        normalized_kinds: list[str] | None = None
        if kinds is not None:
            normalized_kinds = [_validate_kind(kind) for kind in kinds]
        payload: dict[str, Any] = {"query": query, "top_k": top_k}
        if normalized_kinds is not None:
            payload["kinds"] = normalized_kinds
        raw = self._request_json(
            "POST",
            f"/v1/projects/{self._segment(project_id)}/search",
            payload=payload,
            expected=(200,),
        )
        data = raw.get("data") if isinstance(raw, dict) else None
        if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
            raise MemoryApiError("memory API returned an invalid search response", code="decode_error")
        return data

    def patch_memory(
        self,
        project_id: str,
        memory_id: str,
        *,
        expected_revision: int,
        body: str | None = None,
        pinned: bool | None = None,
        superseded_by: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        project_id = _validate_project_id(project_id)
        self._validate_revision(expected_revision)
        if not isinstance(memory_id, str) or not memory_id:
            raise ValueError("memory id is required")
        payload: dict[str, Any] = {"expected_revision": expected_revision}
        if body is not None:
            if not isinstance(body, str) or not body.strip():
                raise ValueError("memory body must be a nonempty string")
            if len(body.encode("utf-8")) > 65536:
                raise ValueError("memory body must be at most 65536 UTF-8 bytes")
            payload["body"] = body
        if pinned is not None:
            payload["pinned"] = pinned
        if superseded_by is not None:
            payload["superseded_by"] = superseded_by
        key = _validate_idempotency_key(
            uuid.uuid4().hex if idempotency_key is None else idempotency_key
        )
        path = (
            f"/v1/projects/{self._segment(project_id)}/memories/"
            f"{self._segment(memory_id)}"
        )
        return self._data_object(
            self._request_json(
                "PATCH",
                path,
                payload=payload,
                headers={"Idempotency-Key": key},
                expected=(200,),
            )
        )

    def delete_memory(
        self,
        project_id: str,
        memory_id: str,
        *,
        expected_revision: int,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        project_id = _validate_project_id(project_id)
        self._validate_revision(expected_revision)
        if not isinstance(memory_id, str) or not memory_id:
            raise ValueError("memory id is required")
        key = _validate_idempotency_key(
            uuid.uuid4().hex if idempotency_key is None else idempotency_key
        )
        path = (
            f"/v1/projects/{self._segment(project_id)}/memories/"
            f"{self._segment(memory_id)}"
        )
        return self._data_object(
            self._request_json(
                "DELETE",
                path,
                payload={"expected_revision": expected_revision},
                headers={"Idempotency-Key": key},
                expected=(200,),
            )
        )

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
        params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
        auth: bool = True,
        expected: tuple[int, ...],
    ) -> dict[str, Any]:
        if auth and not self.token:
            raise MemoryApiConfigurationError("VOSS_MEMORY_API_TOKEN is required for memory API access")
        url = self._url(path, params=params)
        data: bytes | None = None
        request_headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        if auth:
            request_headers["Authorization"] = f"Bearer {self.token}"
        if headers:
            request_headers.update(headers)
        request = urllib.request.Request(url, data=data, headers=request_headers, method=method)

        response: Any | None = None
        try:
            response = self._open(request)
            status = self._response_status(response)
            body = self._read_body(response)
        except urllib.error.HTTPError as exc:
            status = int(exc.code)
            response = exc
            body = self._read_body(exc)
        except (TimeoutError, urllib.error.URLError, OSError) as exc:
            raise MemoryApiUnavailableError(
                "memory API unavailable within the configured timeout", code="unavailable"
            ) from exc
        finally:
            if response is not None:
                self._close(response)

        if status in _REDIRECT_STATUSES:
            raise MemoryApiRedirectError(
                "memory API redirect rejected", status=status, code="redirect_rejected"
            )
        if status not in expected:
            raise self._http_error(status, body)
        if not body:
            return {}
        try:
            decoded = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MemoryApiError("memory API returned invalid JSON", status=status, code="decode_error") from exc
        if not isinstance(decoded, dict):
            raise MemoryApiError("memory API returned an invalid JSON object", status=status, code="decode_error")
        return decoded

    def _open(self, request: urllib.request.Request) -> Any:
        opener = self._opener
        if hasattr(opener, "open"):
            return opener.open(request, timeout=self.timeout)
        if callable(opener):
            return opener(request, timeout=self.timeout)
        raise MemoryApiConfigurationError("memory API transport is not callable")

    @staticmethod
    def _response_status(response: Any) -> int:
        status = getattr(response, "status", None)
        if status is None:
            getcode = getattr(response, "getcode", None)
            status = getcode() if callable(getcode) else None
        try:
            return int(status)
        except (TypeError, ValueError) as exc:
            raise MemoryApiError("memory API returned an invalid status", code="protocol_error") from exc

    @staticmethod
    def _read_body(response: Any) -> bytes:
        try:
            body = response.read(MAX_RESPONSE_BYTES + 1)
        except (OSError, ValueError) as exc:
            raise MemoryApiUnavailableError("memory API response could not be read", code="unavailable") from exc
        if isinstance(body, str):
            body = body.encode("utf-8", errors="replace")
        if not isinstance(body, bytes):
            raise MemoryApiError("memory API returned an invalid response body", code="protocol_error")
        if len(body) > MAX_RESPONSE_BYTES:
            raise MemoryApiError("memory API response exceeded the size limit", code="response_too_large")
        return body

    @staticmethod
    def _close(response: Any) -> None:
        close = getattr(response, "close", None)
        if callable(close):
            close()

    def _http_error(self, status: int, body: bytes) -> MemoryApiError:
        code: str | None = None
        message = f"memory API request failed (HTTP {status})"
        try:
            decoded = json.loads(body.decode("utf-8")) if body else None
        except (UnicodeDecodeError, json.JSONDecodeError):
            decoded = None
        if isinstance(decoded, dict):
            error = decoded.get("error")
            if isinstance(error, dict):
                raw_code = error.get("code")
                raw_message = error.get("message")
                code = str(raw_code) if raw_code else None
                if raw_message:
                    message = str(raw_message)
            elif decoded.get("detail"):
                message = str(decoded["detail"])
        safe = _safe_error_message(message, self.token)
        return MemoryApiError(safe, status=status, code=code)

    @staticmethod
    def _data_object(raw: Mapping[str, Any]) -> dict[str, Any]:
        data = raw.get("data") if isinstance(raw, Mapping) else None
        if isinstance(data, dict):
            return data
        raise MemoryApiError("memory API returned an invalid data object", code="decode_error")

    @staticmethod
    def _validate_revision(revision: int) -> None:
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
            raise ValueError("memory revision must be a positive integer")

    @staticmethod
    def _segment(value: str) -> str:
        return urllib.parse.quote(value, safe="-._~")

    def _url(self, path: str, *, params: Mapping[str, str] | None = None) -> str:
        if not path.startswith("/"):
            raise ValueError("memory API path must start with /")
        url = f"{self.base_url}{path}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        return url


__all__ = [
    "DEFAULT_TIMEOUT_SECONDS",
    "MAX_RESPONSE_BYTES",
    "MemoryApiClient",
    "MemoryApiConfigurationError",
    "MemoryApiError",
    "MemoryApiRedirectError",
    "MemoryApiResponse",
    "MemoryApiUnavailableError",
]

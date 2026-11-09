"""Exception hierarchy for the SneakersRadar API.

Every non-2xx response raises a subclass of :class:`APIStatusError`, chosen by
status code. Network failures raise :class:`APIConnectionError` (or its
:class:`APITimeoutError` subclass).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type

import httpx

__all__ = [
    "APIConnectionError",
    "APIError",
    "APIStatusError",
    "APITimeoutError",
    "AuthenticationError",
    "BadRequestError",
    "ConflictError",
    "InternalServerError",
    "JobTimeoutError",
    "NotFoundError",
    "PermissionDeniedError",
    "RateLimitError",
    "SolometricsError",
    "UnprocessableEntityError",
    "UpstreamError",
    "UpstreamTimeoutError",
]


class SolometricsError(Exception):
    """Base class for every error raised by this SDK."""


class APIError(SolometricsError):
    """An error talking to the API (network failure or non-2xx response)."""

    message: str
    request: Optional[httpx.Request]

    def __init__(self, message: str, *, request: Optional[httpx.Request] = None) -> None:
        super().__init__(message)
        self.message = message
        self.request = request


class APIConnectionError(APIError):
    """The request never produced a response (DNS, TLS, connection reset, ...)."""

    def __init__(self, message: str = "Connection error.", *, request: Optional[httpx.Request] = None) -> None:
        super().__init__(message, request=request)


class APITimeoutError(APIConnectionError):
    """The request timed out on the client side."""

    def __init__(self, *, request: Optional[httpx.Request] = None) -> None:
        super().__init__("Request timed out.", request=request)


class APIStatusError(APIError):
    """The API returned a non-2xx status.

    Attributes:
        status_code: HTTP status code.
        detail: The ``detail`` field of the JSON error body: a message string,
            or a list of field errors for 422. ``None`` if the body had none.
        body: The full decoded JSON body (or raw text if it was not JSON).
        response: The underlying ``httpx.Response``.
    """

    status_code: int
    detail: Any
    body: Any
    response: httpx.Response

    def __init__(self, message: str, *, response: httpx.Response, body: Any) -> None:
        super().__init__(message, request=response.request)
        self.response = response
        self.status_code = response.status_code
        self.body = body
        self.detail = body.get("detail") if isinstance(body, dict) else None

    def __str__(self) -> str:
        return f"{self.status_code}: {self.message}"


class BadRequestError(APIStatusError):
    """400 — invalid request, plan pagination cap, bad CSV, no usable StockX
    connection, or the connection's daily request cap was reached."""


class AuthenticationError(APIStatusError):
    """401 — the API key is missing, invalid or revoked."""


class PermissionDeniedError(APIStatusError):
    """403 — the endpoint is not included in the account's plan."""


class NotFoundError(APIStatusError):
    """404 — style code, size, SKU or record not found (cost endpoints also
    return 404 when no StockX account is linked)."""


class ConflictError(APIStatusError):
    """409 — keep-listing mode skipped the listing, or a GOAT account is needed
    but not linked."""


class UnprocessableEntityError(APIStatusError):
    """422 — a parameter has the wrong type or is out of range.

    ``errors`` holds the list of field errors from ``detail``.
    """

    @property
    def errors(self) -> List[Dict[str, Any]]:
        return self.detail if isinstance(self.detail, list) else []


class RateLimitError(APIStatusError):
    """429 — rate limit exceeded.

    ``retry_after`` is the ``Retry-After`` header in seconds, when present.
    """

    @property
    def retry_after(self) -> Optional[float]:
        return _parse_retry_after(self.response)


class InternalServerError(APIStatusError):
    """5xx not covered by a more specific class."""


class UpstreamError(InternalServerError):
    """502 — the request to StockX/GOAT failed; ``detail`` carries the upstream error."""


class UpstreamTimeoutError(InternalServerError):
    """504 — StockX did not respond in time."""


class JobTimeoutError(SolometricsError):
    """A ``wait_for_*`` helper gave up before the background job finished.

    ``last_status`` is the last status payload seen.
    """

    def __init__(self, task_id: str, last_status: Any) -> None:
        super().__init__(f"Job {task_id} did not finish in time (last status: {_status_of(last_status)})")
        self.task_id = task_id
        self.last_status = last_status


def _status_of(payload: Any) -> Any:
    return payload.get("status") if isinstance(payload, dict) else payload


_STATUS_MAP: Dict[int, Type[APIStatusError]] = {
    400: BadRequestError,
    401: AuthenticationError,
    403: PermissionDeniedError,
    404: NotFoundError,
    409: ConflictError,
    422: UnprocessableEntityError,
    429: RateLimitError,
    502: UpstreamError,
    504: UpstreamTimeoutError,
}


def _parse_retry_after(response: httpx.Response) -> Optional[float]:
    raw = response.headers.get("retry-after")
    if raw is None:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if value >= 0 else None


def _make_status_error(response: httpx.Response) -> APIStatusError:
    try:
        body: Any = response.json()
    except ValueError:
        body = response.text or None

    detail = body.get("detail") if isinstance(body, dict) else None
    if isinstance(detail, str):
        message = detail
    elif isinstance(detail, list):
        parts = []
        for err in detail:
            if isinstance(err, dict):
                loc = ".".join(str(p) for p in err.get("loc", []))
                parts.append(f"{loc}: {err.get('msg')}" if loc else str(err.get("msg")))
            else:
                parts.append(str(err))
        message = "; ".join(parts) or "Validation error"
    elif isinstance(body, str) and body:
        message = body[:500]
    else:
        message = response.reason_phrase or "API error"

    cls = _STATUS_MAP.get(response.status_code)
    if cls is None:
        cls = InternalServerError if response.status_code >= 500 else APIStatusError
    return cls(message, response=response, body=body)

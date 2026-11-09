"""Python SDK for the SneakersRadar API (https://www.sneakers.itbanque.com/docs)."""

from . import types
from ._async_client import AsyncClient
from ._client import Client
from ._exceptions import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    InternalServerError,
    JobTimeoutError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    SolometricsError,
    UnprocessableEntityError,
    UpstreamError,
    UpstreamTimeoutError,
)
from ._version import __version__

__all__ = [
    "APIConnectionError",
    "APIError",
    "APIStatusError",
    "APITimeoutError",
    "AsyncClient",
    "AuthenticationError",
    "BadRequestError",
    "Client",
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
    "__version__",
    "types",
]

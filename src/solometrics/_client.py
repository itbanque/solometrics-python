"""Synchronous client."""

from __future__ import annotations

import time
from typing import Any, Dict, Mapping, Optional, Union

import httpx

from . import _base
from ._base import FinalRequestOptions
from ._exceptions import APIConnectionError, APITimeoutError, _make_status_error
from ._resources import GoatResource, InventoryResource, StockXResource

__all__ = ["Client"]

TimeoutTypes = Union[float, httpx.Timeout, None]


class Client:
    """Synchronous SneakersRadar API client.

    Args:
        api_key: Your ``sr_live_...`` key. Defaults to ``$SOLOMETRICS_API_KEY``.
        base_url: Defaults to ``$SOLOMETRICS_BASE_URL`` or
            ``https://api.sneakers.itbanque.com``.
        timeout: Seconds (or an ``httpx.Timeout``). Default 60s read, 10s connect.
        max_retries: Retries for 429 (all methods), and for 502/503/504 and
            network errors on idempotent methods. Default 2. ``0`` disables.
        connection_id: Default StockX connection for endpoints that accept
            ``connection_id``. Per-call values override it.
        http_client: Bring your own ``httpx.Client`` (proxies, custom TLS, ...).
            The SDK will not close a client you pass in.

    Use as a context manager, or call :meth:`close` when done::

        with Client() as client:
            quotes = client.stockx.market.search("DZ5485-612")
    """

    inventory: InventoryResource
    stockx: StockXResource
    goat: GoatResource

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: TimeoutTypes = _base.DEFAULT_TIMEOUT,
        max_retries: int = _base.DEFAULT_MAX_RETRIES,
        connection_id: Optional[int] = None,
        default_headers: Optional[Mapping[str, str]] = None,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self.api_key = _base.resolve_api_key(api_key)
        self.base_url = _base.resolve_base_url(base_url)
        self.timeout = timeout
        self.max_retries = max_retries
        self.connection_id = connection_id
        self._custom_headers = dict(default_headers or {})
        self._owns_http_client = http_client is None
        self._http = http_client or httpx.Client(timeout=timeout)

        self.inventory = InventoryResource(self)
        self.stockx = StockXResource(self)
        self.goat = GoatResource(self)

    # ------------------------------------------------------------------ lifecycle

    def close(self) -> None:
        if self._owns_http_client:
            self._http.close()

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def with_options(
        self,
        *,
        api_key: Optional[str] = None,
        timeout: Any = _base.OMIT,
        max_retries: Optional[int] = None,
        connection_id: Any = _base.OMIT,
    ) -> Client:
        """Return a copy with some options changed. The copy shares the HTTP
        connection pool, so it is cheap; close only the original."""
        new = Client(
            api_key or self.api_key,
            base_url=self.base_url,
            timeout=self.timeout if timeout is _base.OMIT else timeout,
            max_retries=self.max_retries if max_retries is None else max_retries,
            connection_id=self.connection_id if connection_id is _base.OMIT else connection_id,
            default_headers=self._custom_headers,
            http_client=self._http,
        )
        return new

    # ------------------------------------------------------------------ requests

    def _headers(self) -> Dict[str, str]:
        headers = _base.default_headers(self.api_key)
        headers.update(self._custom_headers)
        return headers

    def _request(self, options: FinalRequestOptions) -> Any:
        max_retries = self.max_retries if options.max_retries is None else options.max_retries
        timeout = self.timeout if options.timeout is None else options.timeout
        url = f"{self.base_url}{options.path}"
        params = _base.clean_params(options.params)

        attempt = 0
        while True:
            try:
                response = self._http.request(
                    options.method,
                    url,
                    params=params or None,
                    json=options.json,
                    files=options.files,
                    headers=self._headers(),
                    timeout=timeout,
                )
            except httpx.HTTPError as exc:
                if attempt < max_retries and _base.should_retry_exception(options.method, exc):
                    time.sleep(_base.retry_delay(attempt, None))
                    attempt += 1
                    continue
                if isinstance(exc, httpx.TimeoutException):
                    raise APITimeoutError(request=_req(exc)) from exc
                raise APIConnectionError(str(exc) or "Connection error.", request=_req(exc)) from exc

            if response.is_success:
                return _parse(response)

            if attempt < max_retries and _base.should_retry_response(options.method, response):
                time.sleep(_base.retry_delay(attempt, response))
                attempt += 1
                continue
            raise _make_status_error(response)

    def get(self, path: str, *, params: Optional[Mapping[str, Any]] = None, **kw: Any) -> Any:
        """Low-level GET for endpoints the SDK does not wrap yet."""
        return self._request(FinalRequestOptions("GET", path, params=dict(params or {}), **kw))

    def post(self, path: str, *, params: Optional[Mapping[str, Any]] = None, json: Any = None, **kw: Any) -> Any:
        return self._request(FinalRequestOptions("POST", path, params=dict(params or {}), json=json, **kw))

    def put(self, path: str, *, params: Optional[Mapping[str, Any]] = None, json: Any = None, **kw: Any) -> Any:
        return self._request(FinalRequestOptions("PUT", path, params=dict(params or {}), json=json, **kw))

    def patch(self, path: str, *, params: Optional[Mapping[str, Any]] = None, json: Any = None, **kw: Any) -> Any:
        return self._request(FinalRequestOptions("PATCH", path, params=dict(params or {}), json=json, **kw))

    def delete(self, path: str, *, params: Optional[Mapping[str, Any]] = None, **kw: Any) -> Any:
        return self._request(FinalRequestOptions("DELETE", path, params=dict(params or {}), **kw))

    def __repr__(self) -> str:
        return f"<solometrics.Client base_url={self.base_url!r}>"


def _parse(response: httpx.Response) -> Any:
    if response.status_code == 204 or not response.content:
        return None
    try:
        return response.json()
    except ValueError:
        return response.text


def _req(exc: httpx.HTTPError) -> Optional[httpx.Request]:
    try:
        return exc.request
    except RuntimeError:
        return None

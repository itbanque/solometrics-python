"""Asynchronous client."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Mapping, Optional

import httpx

from . import _base
from ._async_resources import AsyncGoatResource, AsyncInventoryResource, AsyncStockXResource
from ._base import FinalRequestOptions
from ._client import TimeoutTypes, _parse, _req
from ._exceptions import APIConnectionError, APITimeoutError, _make_status_error

__all__ = ["AsyncClient"]


class AsyncClient:
    """Asynchronous SneakersRadar API client. Same options and methods as
    :class:`~solometrics.Client`; every API method is a coroutine and the
    ``iter_*`` helpers are async iterators::

        async with AsyncClient() as client:
            quotes = await client.stockx.market.search("DZ5485-612")
            async for item in client.inventory.iter_search(brand="Nike"):
                ...
    """

    inventory: AsyncInventoryResource
    stockx: AsyncStockXResource
    goat: AsyncGoatResource

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: TimeoutTypes = _base.DEFAULT_TIMEOUT,
        max_retries: int = _base.DEFAULT_MAX_RETRIES,
        connection_id: Optional[int] = None,
        default_headers: Optional[Mapping[str, str]] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.api_key = _base.resolve_api_key(api_key)
        self.base_url = _base.resolve_base_url(base_url)
        self.timeout = timeout
        self.max_retries = max_retries
        self.connection_id = connection_id
        self._custom_headers = dict(default_headers or {})
        self._owns_http_client = http_client is None
        self._http = http_client or httpx.AsyncClient(timeout=timeout)

        self.inventory = AsyncInventoryResource(self)
        self.stockx = AsyncStockXResource(self)
        self.goat = AsyncGoatResource(self)

    async def close(self) -> None:
        if self._owns_http_client:
            await self._http.aclose()

    async def __aenter__(self) -> AsyncClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    def with_options(
        self,
        *,
        api_key: Optional[str] = None,
        timeout: Any = _base.OMIT,
        max_retries: Optional[int] = None,
        connection_id: Any = _base.OMIT,
    ) -> AsyncClient:
        """Return a copy with some options changed, sharing the connection pool."""
        return AsyncClient(
            api_key or self.api_key,
            base_url=self.base_url,
            timeout=self.timeout if timeout is _base.OMIT else timeout,
            max_retries=self.max_retries if max_retries is None else max_retries,
            connection_id=self.connection_id if connection_id is _base.OMIT else connection_id,
            default_headers=self._custom_headers,
            http_client=self._http,
        )

    def _headers(self) -> Dict[str, str]:
        headers = _base.default_headers(self.api_key)
        headers.update(self._custom_headers)
        return headers

    async def _request(self, options: FinalRequestOptions) -> Any:
        max_retries = self.max_retries if options.max_retries is None else options.max_retries
        timeout = self.timeout if options.timeout is None else options.timeout
        url = f"{self.base_url}{options.path}"
        params = _base.clean_params(options.params)

        attempt = 0
        while True:
            try:
                response = await self._http.request(
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
                    await asyncio.sleep(_base.retry_delay(attempt, None))
                    attempt += 1
                    continue
                if isinstance(exc, httpx.TimeoutException):
                    raise APITimeoutError(request=_req(exc)) from exc
                raise APIConnectionError(str(exc) or "Connection error.", request=_req(exc)) from exc

            if response.is_success:
                return _parse(response)

            if attempt < max_retries and _base.should_retry_response(options.method, response):
                await asyncio.sleep(_base.retry_delay(attempt, response))
                attempt += 1
                continue
            raise _make_status_error(response)

    async def get(self, path: str, *, params: Optional[Mapping[str, Any]] = None, **kw: Any) -> Any:
        """Low-level GET for endpoints the SDK does not wrap yet."""
        return await self._request(FinalRequestOptions("GET", path, params=dict(params or {}), **kw))

    async def post(self, path: str, *, params: Optional[Mapping[str, Any]] = None, json: Any = None, **kw: Any) -> Any:
        return await self._request(FinalRequestOptions("POST", path, params=dict(params or {}), json=json, **kw))

    async def put(self, path: str, *, params: Optional[Mapping[str, Any]] = None, json: Any = None, **kw: Any) -> Any:
        return await self._request(FinalRequestOptions("PUT", path, params=dict(params or {}), json=json, **kw))

    async def patch(self, path: str, *, params: Optional[Mapping[str, Any]] = None, json: Any = None, **kw: Any) -> Any:
        return await self._request(FinalRequestOptions("PATCH", path, params=dict(params or {}), json=json, **kw))

    async def delete(self, path: str, *, params: Optional[Mapping[str, Any]] = None, **kw: Any) -> Any:
        return await self._request(FinalRequestOptions("DELETE", path, params=dict(params or {}), **kw))

    def __repr__(self) -> str:
        return f"<solometrics.AsyncClient base_url={self.base_url!r}>"

"""Synchronous API resources. Mirrors ``_async_resources.py`` method for method."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, Iterator, Optional, Sequence, Union

from . import _base
from ._base import Amount, DateLike, FileInput, FinalRequestOptions, Rows, path_segment
from ._exceptions import JobTimeoutError
from .types import (
    CancelUnlistResponse,
    CostClearResponse,
    CostImportResponse,
    CostListResponse,
    CostRecord,
    HotStylesResponse,
    InventoryItem,
    InventorySearchResponse,
    JobStatus,
    MarketSearchResponse,
    OkResponse,
    Order,
    OrderAnalyticsResponse,
    OrderListResponse,
    OrderSyncResponse,
    SkuHistoryResponse,
    TaskQueuedResponse,
    UnlistJobResponse,
    UnmatchedResponse,
    UploadJobResponse,
    UploadValidationResponse,
)

if TYPE_CHECKING:
    from ._client import Client

__all__ = ["GoatResource", "InventoryResource", "StockXResource"]

Size = Union[str, int, float]


class _Resource:
    def __init__(self, client: Client) -> None:
        self._client = client

    def _conn(self, connection_id: Optional[int]) -> Optional[int]:
        return self._client.connection_id if connection_id is None else connection_id

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._client._request(FinalRequestOptions("GET", path, params=params or {}))

    def _send(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Any = None,
        files: Any = None,
    ) -> Any:
        return self._client._request(FinalRequestOptions(method, path, params=params or {}, json=json, files=files))

    def _wait(
        self,
        fetch: Callable[[], Any],
        task_id: str,
        poll_interval: float,
        timeout: Optional[float],
        on_progress: Optional[Callable[[Any], None]],
    ) -> Any:
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            status = fetch()
            if on_progress is not None:
                on_progress(status)
            if _base.job_finished(status):
                return status
            if deadline is not None and time.monotonic() + poll_interval > deadline:
                raise JobTimeoutError(task_id, status)
            time.sleep(poll_interval)


# =========================================================================== retail


class InventoryResource(_Resource):
    """Retailer inventory and SKU stock history."""

    def search(
        self,
        q: Optional[str] = None,
        *,
        style_color: Optional[str] = None,
        brand: Optional[str] = None,
        retailer: Optional[str] = None,
        size: Optional[Size] = None,
        retailer_sku: Optional[str] = None,
        supplier_sku: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> InventorySearchResponse:
        """``GET /v1/inventory/search`` — one page of SKUs with stock per location.

        ``q`` searches broadly; the other filters are partial matches except
        ``size`` (exact). ``limit`` is capped by your plan's ``max_page_size``.
        """
        return self._get(
            "/v1/inventory/search",
            {
                "q": q,
                "style_color": style_color,
                "brand": brand,
                "retailer": retailer,
                "size": None if size is None else _base.format_size(size),
                "retailer_sku": retailer_sku,
                "supplier_sku": supplier_sku,
                "limit": limit,
                "offset": offset,
            },
        )

    def iter_search(
        self,
        q: Optional[str] = None,
        *,
        style_color: Optional[str] = None,
        brand: Optional[str] = None,
        retailer: Optional[str] = None,
        size: Optional[Size] = None,
        retailer_sku: Optional[str] = None,
        supplier_sku: Optional[str] = None,
        page_size: Optional[int] = None,
        offset: int = 0,
    ) -> Iterator[InventoryItem]:
        """Iterate every matching SKU across pages.

        Stops at the last page. Without provider access for ``retailer`` the
        plan's ``max_page_number`` cap applies, and going past it raises
        :class:`~solometrics.BadRequestError`.
        """
        while True:
            page = self.search(
                q,
                style_color=style_color,
                brand=brand,
                retailer=retailer,
                size=size,
                retailer_sku=retailer_sku,
                supplier_sku=supplier_sku,
                limit=page_size,
                offset=offset,
            )
            items = page.get("items") or []
            for _item in items:
                yield _item
            if not page.get("has_next_page") or not items:
                return
            offset += len(items)

    def history(
        self,
        retailer: str,
        retailer_sku: str,
        *,
        hours: Optional[int] = None,
    ) -> SkuHistoryResponse:
        """``GET /v1/reporting/retailers/{retailer}/skus/{retailer_sku}/history``

        Stock history of one SKU, newest first. ``hours`` is the look-back
        window, 1–8760 (default 168).
        """
        return self._get(
            f"/v1/reporting/retailers/{path_segment(retailer)}/skus/{path_segment(retailer_sku)}/history",
            {"hours": hours},
        )


# =========================================================================== market


class StockXMarketResource(_Resource):
    def search(
        self,
        style_id: str,
        *,
        size: Optional[Size] = None,
        force: Optional[bool] = None,
    ) -> MarketSearchResponse:
        """``GET /v2/stockx/market/search`` — lowest ask / highest bid per size.

        Served from cache when fresh; ``force=True`` skips the cache and spends
        StockX quota. Check ``fetched_at`` for freshness.
        """
        return self._get(
            "/v2/stockx/market/search",
            {
                "style_id": style_id,
                "size": None if size is None else _base.format_size(size),
                "force": force,
            },
        )

    def hot(self, *, limit: Optional[int] = None, page: Optional[int] = None) -> HotStylesResponse:
        """``GET /v2/stockx/market/hot`` — style codes with recently cached quotes."""
        return self._get("/v2/stockx/market/hot", {"limit": limit, "page": page})

    def iter_hot(self, *, page_size: int = 100) -> Iterator[str]:
        """Iterate every recently quoted style code across pages."""
        page = 1
        while True:
            data = self.hot(limit=page_size, page=page)
            for _item in data.get("items") or []:
                yield _item
            if not data.get("has_next"):
                return
            page += 1

    def variant(
        self,
        product_id: str,
        variant_id: str,
        *,
        currency_code: Optional[str] = None,
        connection_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """``GET /v2/stockx/catalog/products/{product_id}/variants/{variant_id}/market-data``

        Live quote for one size. Always calls StockX. Returns StockX's market
        data object as received.
        """
        return self._get(
            f"/v2/stockx/catalog/products/{path_segment(product_id)}/variants/{path_segment(variant_id)}/market-data",
            {"currency_code": currency_code, "connection_id": self._conn(connection_id)},
        )


class StockXCatalogResource(_Resource):
    def search(
        self,
        q: str,
        *,
        page_number: Optional[int] = None,
        page_size: Optional[int] = None,
        connection_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """``GET /v2/stockx/catalog/search`` — StockX catalog search (usually by
        style code), returned as received from StockX."""
        return self._get(
            "/v2/stockx/catalog/search",
            {
                "q": q,
                "page_number": page_number,
                "page_size": page_size,
                "connection_id": self._conn(connection_id),
            },
        )

    def variants(
        self,
        product_id: str,
        *,
        style_id: Optional[str] = None,
        connection_id: Optional[int] = None,
    ) -> Any:
        """``GET /v2/stockx/catalog/products/{product_id}/variants`` — every size
        variant of a product. Pass ``style_id`` so the product is cached."""
        return self._get(
            f"/v2/stockx/catalog/products/{path_segment(product_id)}/variants",
            {"style_id": style_id, "connection_id": self._conn(connection_id)},
        )


# =========================================================================== listings


class StockXListingsResource(_Resource):
    """Create, reprice and take down listings on your linked StockX account."""

    # -------------------------------------------------------------- single items

    def create_by_sku(
        self,
        style_id: str,
        size: Size,
        amount: Amount,
        *,
        cost: Optional[float] = None,
        currency_code: Optional[str] = None,
        expires_at: Any = None,
        active: Optional[bool] = None,
        inventory_type: Optional[str] = None,
        connection_id: Optional[int] = None,
    ) -> Any:
        """``POST /v2/stockx/simple-listing`` — list by style code and size.

        The backend resolves the variant. Raises
        :class:`~solometrics.NotFoundError` if no variant matches and
        :class:`~solometrics.ConflictError` when keep-listing mode skips it.
        Requires the basic plan.
        """
        return self._send(
            "POST",
            "/v2/stockx/simple-listing",
            params={"connection_id": self._conn(connection_id)},
            json=_base.clean_body(
                {
                    "styleId": style_id,
                    "size": _base.format_size(size),
                    "amount": _base.format_amount(amount),
                    "cost": cost,
                    "currencyCode": currency_code,
                    "expiresAt": None if expires_at is None else _base.format_datetime(expires_at),
                    "active": active,
                    "inventoryType": inventory_type,
                }
            ),
        )

    def create(
        self,
        variant_id: str,
        amount: Amount,
        *,
        cost: Optional[float] = None,
        style_id: Optional[str] = None,
        size: Optional[Size] = None,
        currency_code: Optional[str] = None,
        expires_at: Any = None,
        active: Optional[bool] = None,
        inventory_type: Optional[str] = None,
        connection_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """``POST /v2/stockx/listings`` — list a specific ``variant_id``.

        To store a cost record too, pass ``cost``, ``style_id`` and ``size``
        together (the API silently skips the cost if one is missing, so the
        SDK raises ``ValueError`` instead). Requires the basic plan.
        """
        if cost is not None and (style_id is None or size is None):
            raise ValueError("`cost` is only stored together with `style_id` and `size`; pass all three.")
        return self._send(
            "POST",
            "/v2/stockx/listings",
            params={"connection_id": self._conn(connection_id)},
            json=_base.clean_body(
                {
                    "variantId": variant_id,
                    "amount": _base.format_amount(amount),
                    "currencyCode": currency_code,
                    "expiresAt": None if expires_at is None else _base.format_datetime(expires_at),
                    "active": active,
                    "inventoryType": inventory_type,
                    "cost": cost,
                    "styleId": style_id,
                    "size": None if size is None else _base.format_size(size),
                }
            ),
        )

    def update(
        self,
        listing_id: str,
        *,
        amount: Optional[Amount] = None,
        currency_code: Optional[str] = None,
        expires_at: Any = None,
        connection_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """``PATCH /v2/stockx/listings/{listing_id}`` — reprice or change expiry.
        Requires the basic plan."""
        return self._send(
            "PATCH",
            f"/v2/stockx/listings/{path_segment(listing_id)}",
            params={"connection_id": self._conn(connection_id)},
            json=_base.clean_body(
                {
                    "amount": None if amount is None else _base.format_amount(amount),
                    "currencyCode": currency_code,
                    "expiresAt": None if expires_at is None else _base.format_datetime(expires_at),
                }
            ),
        )

    def list(
        self,
        *,
        page_number: Optional[int] = None,
        page_size: Optional[int] = None,
        listing_statuses: Union[str, Sequence[str], None] = None,
        sku: Optional[str] = None,
        connection_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """``GET /v2/stockx/listings`` — your listings, fetched live from StockX.

        ``listing_statuses`` defaults to ``ACTIVE``; pass a list for several.
        ACTIVE listings carry ``cost`` and ``netPrice``. ``sku`` must be a style
        code already cached for your account, otherwise 404.
        """
        return self._get(
            "/v2/stockx/listings",
            {
                "page_number": page_number,
                "page_size": page_size,
                "listing_statuses": _base.join_statuses(listing_statuses),
                "sku": sku,
                "connection_id": self._conn(connection_id),
            },
        )

    def get(self, listing_id: str, *, connection_id: Optional[int] = None) -> Dict[str, Any]:
        """``GET /v2/stockx/listings/{listing_id}`` — one listing."""
        return self._get(
            f"/v2/stockx/listings/{path_segment(listing_id)}",
            {"connection_id": self._conn(connection_id)},
        )

    def get_operation(
        self, listing_id: str, operation_id: str, *, connection_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """``GET /v2/stockx/listings/{listing_id}/operations/{operation_id}`` —
        result of an asynchronous StockX operation."""
        return self._get(
            f"/v2/stockx/listings/{path_segment(listing_id)}/operations/{path_segment(operation_id)}",
            {"connection_id": self._conn(connection_id)},
        )

    def deactivate(self, listing_id: str, *, connection_id: Optional[int] = None) -> Dict[str, Any]:
        """``PUT /v2/stockx/listings/{listing_id}/deactivate`` — take off market,
        keep the listing. Requires the basic plan."""
        return self._send(
            "PUT",
            f"/v2/stockx/listings/{path_segment(listing_id)}/deactivate",
            params={"connection_id": self._conn(connection_id)},
        )

    def activate(
        self,
        listing_id: str,
        *,
        amount: Optional[Amount] = None,
        connection_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """``PUT /v2/stockx/listings/{listing_id}/activate`` — put back on market,
        optionally at a new ``amount``. Requires the basic plan."""
        body = None if amount is None else {"amount": _base.format_amount(amount)}
        return self._send(
            "PUT",
            f"/v2/stockx/listings/{path_segment(listing_id)}/activate",
            params={"connection_id": self._conn(connection_id)},
            json=body,
        )

    def delete(
        self,
        listing_id: str,
        *,
        variant_id: Optional[str] = None,
        connection_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """``DELETE /v2/stockx/listings/{listing_id}`` — permanent. With
        ``variant_id`` the variant's cost records are deleted too. Requires the
        basic plan."""
        return self._send(
            "DELETE",
            f"/v2/stockx/listings/{path_segment(listing_id)}",
            params={"variant_id": variant_id, "connection_id": self._conn(connection_id)},
        )

    def batch_delete(
        self,
        items: Iterable[Any],
        *,
        connection_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """``POST /v2/stockx/batch/delete-listing`` — delete several listings in
        one StockX batch. Requires the advanced plan.

        ``items`` may be listing ID strings, ``(listing_id, variant_id)``
        tuples, or dicts with ``listingId``/``listing_id`` and optional
        ``variantId``/``variant_id``.
        """
        return self._send(
            "POST",
            "/v2/stockx/batch/delete-listing",
            params={"connection_id": self._conn(connection_id)},
            json={"items": _base.normalize_batch_delete_items(items)},
        )

    # -------------------------------------------------------------- CSV upload

    def upload(
        self,
        file: Optional[FileInput] = None,
        *,
        rows: Optional[Rows] = None,
        batch_size: Optional[int] = None,
    ) -> UploadJobResponse:
        """``POST /v2/stockx/listings/upload`` — start a bulk listing job.

        Pass a CSV as ``file`` (path, bytes or file object) or ``rows`` (dicts
        with ``sku, size, quantity, amount, cost``). Returns a ``taskId``; poll
        with :meth:`upload_status` or :meth:`wait_for_upload`. Advanced plan.
        """
        return self._send(
            "POST",
            "/v2/stockx/listings/upload",
            params={"batch_size": batch_size},
            files=_base.prepare_csv_upload(file, rows, default_name="listings.csv"),
        )

    def validate_upload(
        self, file: Optional[FileInput] = None, *, rows: Optional[Rows] = None
    ) -> UploadValidationResponse:
        """``POST /v2/stockx/listings/upload/validate`` — count valid, invalid and
        duplicate rows without listing anything."""
        return self._send(
            "POST",
            "/v2/stockx/listings/upload/validate",
            files=_base.prepare_csv_upload(file, rows, default_name="listings.csv"),
        )

    def upload_status(self, task_id: str) -> JobStatus:
        """``GET /v2/stockx/listings/upload/{task_id}``"""
        return self._get(f"/v2/stockx/listings/upload/{path_segment(task_id)}")

    def wait_for_upload(
        self,
        task_id: str,
        *,
        poll_interval: float = 5.0,
        timeout: Optional[float] = None,
        on_progress: Optional[Callable[[JobStatus], None]] = None,
    ) -> JobStatus:
        """Poll :meth:`upload_status` until the job is SUCCESS, FAILURE or
        CANCELLED, and return the final status. Raises
        :class:`~solometrics.JobTimeoutError` after ``timeout`` seconds."""
        return self._wait(lambda: self.upload_status(task_id), task_id, poll_interval, timeout, on_progress)

    def unmatched(self) -> UnmatchedResponse:
        """``GET /v2/stockx/listings/upload/unmatched`` — uploaded rows that could
        not be matched to a variant."""
        return self._get("/v2/stockx/listings/upload/unmatched")

    # -------------------------------------------------------------- CSV unlist

    def unlist(self, file: Optional[FileInput] = None, *, rows: Optional[Rows] = None) -> UnlistJobResponse:
        """``POST /v2/stockx/listings/unlist`` — start a bulk delist job.

        Rows carry ``listing_id`` (optionally ``variant_id``), or ``sku`` (or
        ``style_id``) plus ``size`` to match ACTIVE listings. Advanced plan.
        """
        return self._send(
            "POST",
            "/v2/stockx/listings/unlist",
            files=_base.prepare_csv_upload(file, rows, default_name="unlist.csv"),
        )

    def unlist_status(self, task_id: str) -> JobStatus:
        """``GET /v2/stockx/listings/unlist/{task_id}``"""
        return self._get(f"/v2/stockx/listings/unlist/{path_segment(task_id)}")

    def wait_for_unlist(
        self,
        task_id: str,
        *,
        poll_interval: float = 5.0,
        timeout: Optional[float] = None,
        on_progress: Optional[Callable[[JobStatus], None]] = None,
    ) -> JobStatus:
        """Poll :meth:`unlist_status` until the job finishes."""
        return self._wait(lambda: self.unlist_status(task_id), task_id, poll_interval, timeout, on_progress)

    def cancel_unlist(self) -> CancelUnlistResponse:
        """``POST /v2/stockx/listings/unlist/cancel`` — cancel your running unlist job."""
        return self._send("POST", "/v2/stockx/listings/unlist/cancel")

    # -------------------------------------------------------------- clear all

    def clear_all(self) -> TaskQueuedResponse:
        """``POST /v2/stockx/listings/clear-all`` — delete EVERY active listing in
        the account's ``clear_all_scope``. Cannot be undone. Advanced plan."""
        return self._send("POST", "/v2/stockx/listings/clear-all")

    def clear_all_status(self, task_id: str) -> JobStatus:
        """``GET /v2/stockx/listings/clear-all/{task_id}``"""
        return self._get(f"/v2/stockx/listings/clear-all/{path_segment(task_id)}")

    def wait_for_clear_all(
        self,
        task_id: str,
        *,
        poll_interval: float = 5.0,
        timeout: Optional[float] = None,
        on_progress: Optional[Callable[[JobStatus], None]] = None,
    ) -> JobStatus:
        """Poll :meth:`clear_all_status` until the job finishes."""
        return self._wait(lambda: self.clear_all_status(task_id), task_id, poll_interval, timeout, on_progress)


# =========================================================================== costs


class StockXCostsResource(_Resource):
    """Acquisition costs per style code / size / variant. Uses no StockX quota."""

    def set(
        self,
        style_id: str,
        size: Size,
        variant_id: str,
        cost: float,
        *,
        connection_id: Optional[int] = None,
    ) -> OkResponse:
        """``PATCH /v2/stockx/cost`` — create or overwrite the cost for one
        style/size/variant. Requires the basic plan."""
        return self._send(
            "PATCH",
            "/v2/stockx/cost",
            params={"connection_id": self._conn(connection_id)},
            json={"styleId": style_id, "size": _base.format_size(size), "variantId": variant_id, "cost": cost},
        )

    def list(
        self,
        *,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        style_id: Optional[str] = None,
        connection_id: Optional[int] = None,
    ) -> CostListResponse:
        """``GET /v2/stockx/costs`` — cost records, newest first. ``page_size``
        is 1–200 (default 50); ``style_id`` is a partial match."""
        return self._get(
            "/v2/stockx/costs",
            {
                "page": page,
                "page_size": page_size,
                "style_id": style_id,
                "connection_id": self._conn(connection_id),
            },
        )

    def iter_list(
        self,
        *,
        page_size: int = 200,
        style_id: Optional[str] = None,
        connection_id: Optional[int] = None,
    ) -> Iterator[CostRecord]:
        """Iterate every cost record across pages."""
        page = 1
        seen = 0
        while True:
            data = self.list(page=page, page_size=page_size, style_id=style_id, connection_id=connection_id)
            items = data.get("items") or []
            for _item in items:
                yield _item
            seen += len(items)
            if not items or seen >= int(data.get("total") or 0):
                return
            page += 1

    def import_csv(
        self,
        file: Optional[FileInput] = None,
        *,
        rows: Optional[Rows] = None,
        connection_id: Optional[int] = None,
    ) -> CostImportResponse:
        """``POST /v2/stockx/costs/import`` — upsert costs from a CSV with
        ``style_id, size, variant_id, cost``. Synchronous. Advanced plan."""
        return self._send(
            "POST",
            "/v2/stockx/costs/import",
            params={"connection_id": self._conn(connection_id)},
            files=_base.prepare_csv_upload(file, rows, default_name="costs.csv"),
        )

    def update(
        self,
        cost_id: int,
        *,
        cost: Optional[float] = None,
        is_active: Optional[bool] = None,
        connection_id: Optional[int] = None,
    ) -> OkResponse:
        """``PATCH /v2/stockx/costs/{cost_id}`` — edit one record.
        ``is_active=False`` keeps it but excludes it from profit and smart
        pricing. Requires the basic plan."""
        return self._send(
            "PATCH",
            f"/v2/stockx/costs/{path_segment(cost_id)}",
            params={"connection_id": self._conn(connection_id)},
            json=_base.clean_body({"cost": cost, "is_active": is_active}),
        )

    def clear(self, *, connection_id: Optional[int] = None) -> CostClearResponse:
        """``DELETE /v2/stockx/costs`` — delete EVERY cost record on the
        connection. Cannot be undone. Requires the basic plan."""
        return self._send("DELETE", "/v2/stockx/costs", params={"connection_id": self._conn(connection_id)})


# =========================================================================== orders


class StockXOrdersResource(_Resource):
    """Locally synced StockX orders. All endpoints need the advanced plan."""

    def sync(self) -> OrderSyncResponse:
        """``POST /v2/stockx/orders/sync`` — start a background sync from StockX."""
        return self._send("POST", "/v2/stockx/orders/sync")

    def list(
        self,
        *,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        order_status: Optional[str] = None,
        from_date: Optional[DateLike] = None,
        to_date: Optional[DateLike] = None,
        search: Optional[str] = None,
    ) -> OrderListResponse:
        """``GET /v2/stockx/orders`` — synced orders, newest first."""
        return self._get(
            "/v2/stockx/orders",
            {
                "page": page,
                "page_size": page_size,
                "order_status": order_status,
                "from_date": None if from_date is None else _base.format_date(from_date),
                "to_date": None if to_date is None else _base.format_date(to_date),
                "search": search,
            },
        )

    def iter_list(
        self,
        *,
        page_size: int = 200,
        order_status: Optional[str] = None,
        from_date: Optional[DateLike] = None,
        to_date: Optional[DateLike] = None,
        search: Optional[str] = None,
    ) -> Iterator[Order]:
        """Iterate every matching order across pages."""
        page = 1
        seen = 0
        while True:
            data = self.list(
                page=page,
                page_size=page_size,
                order_status=order_status,
                from_date=from_date,
                to_date=to_date,
                search=search,
            )
            orders = data.get("orders") or []
            for _item in orders:
                yield _item
            seen += len(orders)
            if not orders or seen >= int(data.get("total") or 0):
                return
            page += 1

    def analytics(
        self,
        *,
        from_date: Optional[DateLike] = None,
        to_date: Optional[DateLike] = None,
        granularity: Optional[str] = None,
    ) -> OrderAnalyticsResponse:
        """``GET /v2/stockx/orders/analytics`` — summary, top products/brands,
        sales trend and status breakdown. ``granularity``: daily, weekly or
        monthly (default)."""
        return self._get(
            "/v2/stockx/orders/analytics",
            {
                "from_date": None if from_date is None else _base.format_date(from_date),
                "to_date": None if to_date is None else _base.format_date(to_date),
                "granularity": granularity,
            },
        )


# =========================================================================== groups


class StockXResource(_Resource):
    market: StockXMarketResource
    catalog: StockXCatalogResource
    listings: StockXListingsResource
    costs: StockXCostsResource
    orders: StockXOrdersResource

    def __init__(self, client: Client) -> None:
        super().__init__(client)
        self.market = StockXMarketResource(client)
        self.catalog = StockXCatalogResource(client)
        self.listings = StockXListingsResource(client)
        self.costs = StockXCostsResource(client)
        self.orders = StockXOrdersResource(client)


class GoatMarketResource(_Resource):
    def search(self, style_id: str) -> MarketSearchResponse:
        """``GET /v2/goat/market/search`` — per-size GOAT prices. Needs a linked
        GOAT account (409 otherwise)."""
        return self._get("/v2/goat/market/search", {"style_id": style_id})


class GoatResource(_Resource):
    market: GoatMarketResource

    def __init__(self, client: Client) -> None:
        super().__init__(client)
        self.market = GoatMarketResource(client)

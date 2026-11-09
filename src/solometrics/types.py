"""Typed shapes of documented responses.

These are ``TypedDict`` s: responses are plain ``dict`` objects at runtime, the
types only help editors and type checkers. Endpoints that pass StockX's own
response through unchanged (catalog search, variant list, listing detail, ...)
are typed as ``Dict[str, Any]``.
"""

from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional

if sys.version_info >= (3, 11):
    from typing import TypedDict
else:  # pragma: no cover
    from typing_extensions import TypedDict

__all__ = [
    "CancelUnlistResponse",
    "CostClearResponse",
    "CostImportResponse",
    "CostListResponse",
    "CostRecord",
    "HotStylesResponse",
    "InventoryItem",
    "InventoryLocation",
    "InventoryProduct",
    "InventorySearchResponse",
    "InventorySku",
    "JobStatus",
    "MarketSearchResponse",
    "MarketVariant",
    "OkResponse",
    "Order",
    "OrderAnalyticsResponse",
    "OrderAnalyticsSummary",
    "OrderListResponse",
    "OrderSyncResponse",
    "SalesTrendPoint",
    "SkuHistoryRecord",
    "SkuHistoryResponse",
    "SkuHistorySku",
    "StatusCount",
    "TaskQueuedResponse",
    "TopBrand",
    "TopProduct",
    "UnlistJobResponse",
    "UnmatchedResponse",
    "UploadJobResponse",
    "UploadValidationResponse",
]


# ------------------------------------------------------------------ retail data


class InventorySku(TypedDict, total=False):
    id: int
    retailer: str
    size: str
    retailer_sku: str
    supplier_sku: Optional[str]
    title: Optional[str]
    original_price: Optional[float]
    price: Optional[float]
    coupon_code_eligible: Optional[bool]


class InventoryProduct(TypedDict, total=False):
    id: int
    style_color: str
    brand: Optional[str]
    model_name: Optional[str]
    gender: Optional[str]


class InventoryLocation(TypedDict, total=False):
    location_code: str
    stock_level: str  # HIGH | MEDIUM | LOW | OOS | IN_STOCK
    as_of: str


class InventoryItem(TypedDict, total=False):
    sku: InventorySku
    product: InventoryProduct
    inventory: List[InventoryLocation]


class InventorySearchResponse(TypedDict, total=False):
    total_skus: int
    count: int
    limit: int
    offset: int
    has_next_page: bool
    items: List[InventoryItem]


class SkuHistoryRecord(TypedDict, total=False):
    stock_level: str
    location: str
    record_created_at: str
    price: Optional[float]
    original_price: Optional[float]
    coupon_code_eligible: Optional[bool]


class SkuHistorySku(TypedDict, total=False):
    retailer_sku: str
    size: str
    style_color: str
    model_name: Optional[str]
    brand: Optional[str]


class SkuHistoryResponse(TypedDict, total=False):
    retailer: str
    cutoff_ts: str
    sku: SkuHistorySku
    history: List[SkuHistoryRecord]
    count: int
    limit: Optional[int]
    has_more: bool


# ------------------------------------------------------------------ market data


class MarketVariant(TypedDict, total=False):
    size: str
    lowestAsk: Optional[float]
    highestBid: Optional[float]
    lastSale: Optional[float]
    currency: str
    # GOAT only, depending on how the account is connected
    highDemandPrice: Optional[float]
    productCondition: str
    packagingCondition: str
    regionId: Any


class MarketSearchResponse(TypedDict, total=False):
    platform: str  # "stockx" | "goat"
    style_id: str
    fetched_at: str
    variants: List[MarketVariant]


class HotStylesResponse(TypedDict, total=False):
    items: List[str]
    total: int
    page: int
    limit: int
    pages: int
    has_next: bool
    has_prev: bool


# ------------------------------------------------------------------ listings


class OkResponse(TypedDict, total=False):
    ok: bool


class UploadJobResponse(TypedDict, total=False):
    taskId: str
    status: str
    filename: str
    processedRows: int
    batchSize: int
    duplicateRowsRemoved: int


class UploadValidationResponse(TypedDict, total=False):
    filename: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int


class UnlistJobResponse(TypedDict, total=False):
    taskId: str
    status: str
    filename: str
    processedRows: int
    duplicateRowsRemoved: int
    resolveRows: int


class JobStatus(TypedDict, total=False):
    """Background job progress.

    ``status`` is ``PENDING`` / ``STARTED`` / ``PAUSED`` while running and
    ``SUCCESS`` / ``FAILURE`` / ``CANCELLED`` when finished. ``result`` holds
    job-specific progress counters (``None`` until the job starts).
    """

    taskId: str
    status: str
    result: Optional[Dict[str, Any]]


class UnmatchedResponse(TypedDict, total=False):
    items: List[Any]


class CancelUnlistResponse(TypedDict, total=False):
    cancelled: bool
    result: Any


class TaskQueuedResponse(TypedDict, total=False):
    taskId: str
    status: str


# ------------------------------------------------------------------ costs


class CostRecord(TypedDict, total=False):
    id: int
    style_id: str
    size: str
    variant_id: str
    cost: float
    is_active: bool
    updated_at: str


class CostListResponse(TypedDict, total=False):
    items: List[CostRecord]
    total: int
    page: int
    page_size: int


class CostImportResponse(TypedDict, total=False):
    total_rows: int
    imported: int
    skipped: int


class CostClearResponse(TypedDict, total=False):
    ok: bool
    deleted: int


# ------------------------------------------------------------------ orders


class OrderSyncResponse(TypedDict, total=False):
    task_id: str
    status: str


class Order(TypedDict, total=False):
    id: int
    order_number: str
    listing_id: Optional[str]
    amount: Optional[float]
    currency_code: Optional[str]
    status: Optional[str]
    inventory_type: Optional[str]
    order_created_at: Optional[str]
    order_updated_at: Optional[str]
    product_id: Optional[str]
    product_name: Optional[str]
    style_id: Optional[str]
    variant_id: Optional[str]
    variant_name: Optional[str]
    variant_value: Optional[str]
    total_payout: Optional[float]
    sale_price: Optional[float]
    total_adjustments: Optional[float]
    payout_currency: Optional[str]
    auth_status: Optional[str]


class OrderListResponse(TypedDict, total=False):
    total: int
    page: int
    page_size: int
    orders: List[Order]


class OrderAnalyticsSummary(TypedDict, total=False):
    total_orders: int
    total_revenue: float
    avg_payout: float
    total_fees: float


class TopProduct(TypedDict, total=False):
    product_name: str
    style_id: Optional[str]
    units_sold: int
    total_revenue: float
    avg_payout: float


class TopBrand(TypedDict, total=False):
    brand: str
    units_sold: int
    total_revenue: float


class SalesTrendPoint(TypedDict, total=False):
    period: str
    units: int
    revenue: float


class StatusCount(TypedDict, total=False):
    status: str
    count: int


class OrderAnalyticsResponse(TypedDict, total=False):
    summary: OrderAnalyticsSummary
    top_products: List[TopProduct]
    top_brands: List[TopBrand]
    sales_trend: List[SalesTrendPoint]
    status_breakdown: List[StatusCount]

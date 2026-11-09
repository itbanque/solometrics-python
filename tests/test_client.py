from __future__ import annotations

import io
from datetime import date

import httpx
import pytest

import solometrics
from solometrics import Client

from .conftest import BASE, Recorder

# ----------------------------------------------------------------- auth & config


def test_api_key_header_and_user_agent(client: Client, rec: Recorder) -> None:
    client.stockx.market.hot()
    assert rec.last.headers["X-API-Key"] == "sr_live_test"
    assert rec.last.headers["User-Agent"].startswith("solometrics-python/")


def test_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SOLOMETRICS_API_KEY", "sr_live_env")
    c = Client()
    assert c.api_key == "sr_live_env"
    assert c.base_url == "https://api.sneakers.itbanque.com"
    c.close()


def test_missing_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SOLOMETRICS_API_KEY", raising=False)
    with pytest.raises(ValueError):
        Client()


# ----------------------------------------------------------------- retail data


def test_inventory_search_params(client: Client, rec: Recorder) -> None:
    client.inventory.search(brand="Nike", size=10.0, limit=5, offset=0)
    assert rec.last.method == "GET"
    assert rec.last.url.path == "/v1/inventory/search"
    assert dict(rec.last.url.params) == {"brand": "Nike", "size": "10", "limit": "5", "offset": "0"}


def test_inventory_iter_search_paginates(client: Client, rec: Recorder) -> None:
    pages = {
        "0": {"items": [{"sku": {"id": 1}}, {"sku": {"id": 2}}], "has_next_page": True},
        "2": {"items": [{"sku": {"id": 3}}], "has_next_page": False},
    }
    rec.handler = lambda r: httpx.Response(200, json=pages[r.url.params["offset"]])
    ids = [it["sku"]["id"] for it in client.inventory.iter_search(brand="Nike", page_size=2)]
    assert ids == [1, 2, 3]
    assert len(rec.requests) == 2


def test_sku_history_path_is_encoded(client: Client, rec: Recorder) -> None:
    client.inventory.history("DICKS", "AB/12 3", hours=4320)
    assert rec.last.url.raw_path.decode().startswith("/v1/reporting/retailers/DICKS/skus/AB%2F12%203/history")
    assert rec.last.url.params["hours"] == "4320"


# ----------------------------------------------------------------- market data


def test_stockx_market_search(client: Client, rec: Recorder) -> None:
    rec.handler = lambda r: httpx.Response(200, json={"platform": "stockx", "variants": []})
    out = client.stockx.market.search("DZ5485-612", size="10.5", force=True)
    assert out["platform"] == "stockx"
    assert dict(rec.last.url.params) == {"style_id": "DZ5485-612", "size": "10.5", "force": "true"}


def test_default_connection_id_and_override(rec: Recorder) -> None:
    http = httpx.Client(transport=httpx.MockTransport(rec))
    c = Client("k", base_url=BASE, http_client=http, connection_id=7)
    c.stockx.market.variant("p1", "v1")
    assert rec.last.url.path == "/v2/stockx/catalog/products/p1/variants/v1/market-data"
    assert rec.last.url.params["connection_id"] == "7"
    c.stockx.catalog.search("DZ5485-612", connection_id=9)
    assert rec.last.url.params["connection_id"] == "9"
    c.with_options(connection_id=None).stockx.catalog.variants("p1", style_id="DZ5485-612")
    assert "connection_id" not in rec.last.url.params


def test_iter_hot(client: Client, rec: Recorder) -> None:
    pages = {"1": {"items": ["A", "B"], "has_next": True}, "2": {"items": ["C"], "has_next": False}}
    rec.handler = lambda r: httpx.Response(200, json=pages[r.url.params["page"]])
    assert list(client.stockx.market.iter_hot(page_size=2)) == ["A", "B", "C"]


def test_goat_market(client: Client, rec: Recorder) -> None:
    client.goat.market.search("U9060JBR")
    assert rec.last.url.path == "/v2/goat/market/search"


# ----------------------------------------------------------------- listings


def test_create_by_sku_body(client: Client, rec: Recorder) -> None:
    rec.handler = lambda r: httpx.Response(201, json={"ok": True})
    assert client.stockx.listings.create_by_sku("DZ5485-612", 10, 250.0, cost=180) == {"ok": True}
    assert rec.last.method == "POST"
    assert rec.last.url.path == "/v2/stockx/simple-listing"
    assert rec.last_json() == {"styleId": "DZ5485-612", "size": "10", "amount": "250", "cost": 180}


def test_create_requires_style_and_size_with_cost(client: Client) -> None:
    with pytest.raises(ValueError):
        client.stockx.listings.create("v1", 250, cost=180)


def test_create_by_variant(client: Client, rec: Recorder) -> None:
    client.stockx.listings.create("v1", "250", currency_code="USD", active=False, cost=180, style_id="S", size="10")
    assert rec.last_json() == {
        "variantId": "v1",
        "amount": "250",
        "currencyCode": "USD",
        "active": False,
        "cost": 180,
        "styleId": "S",
        "size": "10",
    }


def test_update_and_activate(client: Client, rec: Recorder) -> None:
    client.stockx.listings.update("L-1001", amount=260)
    assert rec.last.method == "PATCH" and rec.last_json() == {"amount": "260"}
    client.stockx.listings.activate("L-1001")
    assert rec.last.method == "PUT" and rec.last.content == b""
    client.stockx.listings.activate("L-1001", amount=240)
    assert rec.last_json() == {"amount": "240"}


def test_list_listings_statuses(client: Client, rec: Recorder) -> None:
    client.stockx.listings.list(listing_statuses=["ACTIVE", "INACTIVE"], sku="DZ5485-612")
    assert rec.last.url.params["listing_statuses"] == "ACTIVE,INACTIVE"


def test_delete_with_variant(client: Client, rec: Recorder) -> None:
    client.stockx.listings.delete("L-1001", variant_id="v1")
    assert rec.last.method == "DELETE"
    assert rec.last.url.params["variant_id"] == "v1"


def test_batch_delete_normalizes_items(client: Client, rec: Recorder) -> None:
    client.stockx.listings.batch_delete(["L-1", ("L-2", "v2"), {"listing_id": "L-3", "variant_id": "v3"}])
    assert rec.last_json() == {
        "items": [
            {"listingId": "L-1"},
            {"listingId": "L-2", "variantId": "v2"},
            {"listingId": "L-3", "variantId": "v3"},
        ]
    }


def test_upload_from_rows(client: Client, rec: Recorder) -> None:
    rec.handler = lambda r: httpx.Response(200, json={"taskId": "t1", "status": "queued"})
    out = client.stockx.listings.upload(
        rows=[{"sku": "DZ5485-612", "size": "10", "quantity": 1, "amount": 250, "cost": 180}], batch_size=50
    )
    assert out["taskId"] == "t1"
    assert rec.last.url.params["batch_size"] == "50"
    body = rec.last.content
    assert b'filename="listings.csv"' in body
    assert b"sku,size,quantity,amount,cost\nDZ5485-612,10,1,250,180\n" in body


def test_upload_from_path_and_fileobj(client: Client, rec: Recorder, tmp_path) -> None:
    p = tmp_path / "mine.csv"
    p.write_text("sku,size,quantity,amount,cost\n")
    client.stockx.listings.validate_upload(p)
    assert b'filename="mine.csv"' in rec.last.content
    client.stockx.costs.import_csv(io.BytesIO(b"style_id,size,variant_id,cost\n"))
    assert b'filename="costs.csv"' in rec.last.content


def test_upload_needs_exactly_one_source(client: Client) -> None:
    with pytest.raises(TypeError):
        client.stockx.listings.upload()


def test_wait_for_upload(client: Client, rec: Recorder) -> None:
    statuses = iter(["PENDING", "STARTED", "SUCCESS"])
    rec.handler = lambda r: httpx.Response(200, json={"taskId": "t1", "status": next(statuses), "result": {}})
    seen = []
    final = client.stockx.listings.wait_for_upload(
        "t1", poll_interval=0, on_progress=lambda s: seen.append(s["status"])
    )
    assert final["status"] == "SUCCESS"
    assert seen == ["PENDING", "STARTED", "SUCCESS"]


def test_wait_timeout(client: Client, rec: Recorder) -> None:
    rec.handler = lambda r: httpx.Response(200, json={"taskId": "t1", "status": "STARTED"})
    with pytest.raises(solometrics.JobTimeoutError) as ei:
        client.stockx.listings.wait_for_clear_all("t1", poll_interval=1, timeout=0)
    assert ei.value.last_status["status"] == "STARTED"


# ----------------------------------------------------------------- costs & orders


def test_cost_set_and_update(client: Client, rec: Recorder) -> None:
    client.stockx.costs.set("DZ5485-612", "10", "v1", 180)
    assert rec.last.url.path == "/v2/stockx/cost"
    assert rec.last_json() == {"styleId": "DZ5485-612", "size": "10", "variantId": "v1", "cost": 180}
    client.stockx.costs.update(4417, is_active=False)
    assert rec.last.url.path == "/v2/stockx/costs/4417"
    assert rec.last_json() == {"is_active": False}


def test_costs_iter(client: Client, rec: Recorder) -> None:
    pages = {"1": {"items": [{"id": 1}, {"id": 2}], "total": 3}, "2": {"items": [{"id": 3}], "total": 3}}
    rec.handler = lambda r: httpx.Response(200, json=pages[r.url.params["page"]])
    assert [c["id"] for c in client.stockx.costs.iter_list(page_size=2)] == [1, 2, 3]


def test_orders_dates(client: Client, rec: Recorder) -> None:
    client.stockx.orders.list(from_date=date(2026, 1, 1), to_date="2026-07-27", order_status="COMPLETED")
    assert rec.last.url.params["from_date"] == "2026-01-01"
    assert rec.last.url.params["to_date"] == "2026-07-27"
    client.stockx.orders.analytics(granularity="weekly")
    assert rec.last.url.path == "/v2/stockx/orders/analytics"


# ----------------------------------------------------------------- errors & retries


@pytest.mark.parametrize(
    "status,body,exc",
    [
        (400, {"detail": "limit exceeds your plan cap"}, solometrics.BadRequestError),
        (401, {"detail": "Not authenticated"}, solometrics.AuthenticationError),
        (403, {"detail": "StockX batch operations require the advanced plan"}, solometrics.PermissionDeniedError),
        (404, {"detail": "No variant found"}, solometrics.NotFoundError),
        (409, {"detail": "Listing skipped"}, solometrics.ConflictError),
        (500, {"detail": "boom"}, solometrics.InternalServerError),
    ],
)
def test_error_mapping(client: Client, rec: Recorder, status, body, exc) -> None:
    rec.handler = lambda r: httpx.Response(status, json=body)
    with pytest.raises(exc) as ei:
        client.stockx.market.search("X")
    assert ei.value.status_code == status
    assert ei.value.detail == body["detail"]
    assert len(rec.requests) == 1  # never retried


def test_422_field_errors(client: Client, rec: Recorder) -> None:
    detail = [{"loc": ["query", "hours"], "msg": "Input should be less than or equal to 8760"}]
    rec.handler = lambda r: httpx.Response(422, json={"detail": detail})
    with pytest.raises(solometrics.UnprocessableEntityError) as ei:
        client.inventory.history("DICKS", "1", hours=99999)
    assert ei.value.errors == detail
    assert "query.hours" in str(ei.value)


def test_429_retried_then_succeeds(client: Client, rec: Recorder) -> None:
    responses = iter(
        [
            httpx.Response(429, headers={"Retry-After": "1"}, json={"detail": "Too Many Requests"}),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    rec.handler = lambda r: next(responses)
    # POST is retried on 429: the request was rejected before processing
    assert client.stockx.listings.create_by_sku("S", "10", 250) == {"ok": True}
    assert len(rec.requests) == 2


def test_429_exhausted(client: Client, rec: Recorder) -> None:
    rec.handler = lambda r: httpx.Response(429, headers={"Retry-After": "3"}, json={"detail": "Too Many Requests"})
    with pytest.raises(solometrics.RateLimitError) as ei:
        client.stockx.market.hot()
    assert ei.value.retry_after == 3.0
    assert len(rec.requests) == 3  # 1 + max_retries(2)


def test_502_retried_for_get_not_post(client: Client, rec: Recorder) -> None:
    rec.handler = lambda r: httpx.Response(502, json={"detail": "StockX failed"})
    with pytest.raises(solometrics.UpstreamError):
        client.stockx.listings.list()
    assert len(rec.requests) == 3
    rec.requests.clear()
    with pytest.raises(solometrics.UpstreamError):
        client.stockx.listings.create_by_sku("S", "10", 250)
    assert len(rec.requests) == 1


def test_504_maps_to_upstream_timeout(client: Client, rec: Recorder) -> None:
    rec.handler = lambda r: httpx.Response(504, json={"detail": "StockX is not responding"})
    with pytest.raises(solometrics.UpstreamTimeoutError):
        client.with_options(max_retries=0).stockx.listings.list()


def test_connect_error(client: Client, rec: Recorder) -> None:
    def boom(r: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=r)

    rec.handler = boom
    with pytest.raises(solometrics.APIConnectionError):
        client.stockx.market.hot()
    assert len(rec.requests) == 3


def test_read_timeout_not_retried_for_post(client: Client, rec: Recorder) -> None:
    def slow(r: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=r)

    rec.handler = slow
    with pytest.raises(solometrics.APITimeoutError):
        client.stockx.listings.create_by_sku("S", "10", 250)
    assert len(rec.requests) == 1

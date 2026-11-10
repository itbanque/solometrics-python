# solometrics — SneakersRadar API Python SDK

[![CI](https://github.com/itbanque/solometrics-python/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/itbanque/solometrics-python/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/solometrics)](https://pypi.org/project/solometrics/)
[![GitHub release](https://img.shields.io/github/v/release/itbanque/solometrics-python)](https://github.com/itbanque/solometrics-python/releases)
[![Python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://pypi.org/project/solometrics/)
[![Wheel](https://img.shields.io/pypi/wheel/solometrics)](https://pypi.org/project/solometrics/#files)
[![Status](https://img.shields.io/pypi/status/solometrics)](https://pypi.org/project/solometrics/)
[![Downloads](https://static.pepy.tech/badge/solometrics)](https://pepy.tech/project/solometrics)
[![Downloads/month](https://img.shields.io/pypi/dm/solometrics)](https://pypistats.org/packages/solometrics)
[![License](https://img.shields.io/github/license/itbanque/solometrics-python)](LICENSE)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![API docs](https://img.shields.io/badge/API-docs-35CC91)](https://www.sneakers.itbanque.com/docs)

Python client for the [SneakersRadar API](https://www.sneakers.itbanque.com/docs): retailer inventory and SKU history, StockX / GOAT market quotes, and StockX listings, costs and orders.

- Sync `Client` and async `AsyncClient` with identical methods
- Typed responses (`TypedDict`), plain `dict` at runtime
- Typed exceptions per status code (`NotFoundError`, `RateLimitError`, ...)
- Automatic retries with backoff, honouring `Retry-After`
- Auto-pagination (`iter_*`) and background-job polling (`wait_for_*`)
- CSV uploads from a path, bytes, file object, or a list of dicts
- One runtime dependency: `httpx`

Python 3.9+.

## Install

```bash
pip install solometrics
# or from source
pip install git+https://github.com/itbanque/solometrics-python
```

## Quick start

Generate a key at <https://www.sneakers.itbanque.com/account> → **API Keys**.

```python
from solometrics import Client

client = Client(api_key="sr_live_...")  # or set SOLOMETRICS_API_KEY

quotes = client.stockx.market.search("DZ5485-612")
for v in quotes["variants"]:
    print(v["size"], v["lowestAsk"], v["highestBid"])
```

Async:

```python
import asyncio
from solometrics import AsyncClient

async def main():
    async with AsyncClient() as client:
        stockx, goat = await asyncio.gather(
            client.stockx.market.search("U9060JBR"),
            client.goat.market.search("U9060JBR"),
        )

asyncio.run(main())
```

## Endpoint map

| SDK method | HTTP | Plan |
|---|---|---|
| **Retail data** | | |
| `inventory.search(q=, style_color=, brand=, retailer=, size=, retailer_sku=, supplier_sku=, limit=, offset=)` | `GET /v1/inventory/search` | data |
| `inventory.iter_search(...)` | auto-paginates the above | data |
| `inventory.history(retailer, retailer_sku, hours=)` | `GET /v1/reporting/retailers/{retailer}/skus/{sku}/history` | data |
| **Market data** | | |
| `stockx.market.search(style_id, size=, force=)` | `GET /v2/stockx/market/search` | |
| `stockx.market.hot(limit=, page=)` / `iter_hot()` | `GET /v2/stockx/market/hot` | |
| `stockx.market.variant(product_id, variant_id, currency_code=)` | `GET /v2/stockx/catalog/products/{p}/variants/{v}/market-data` | free |
| `goat.market.search(style_id)` | `GET /v2/goat/market/search` | |
| **StockX catalog** | | |
| `stockx.catalog.search(q, page_number=, page_size=)` | `GET /v2/stockx/catalog/search` | free |
| `stockx.catalog.variants(product_id, style_id=)` | `GET /v2/stockx/catalog/products/{p}/variants` | free |
| **StockX listings** | | |
| `stockx.listings.create_by_sku(style_id, size, amount, cost=, ...)` | `POST /v2/stockx/simple-listing` | basic |
| `stockx.listings.create(variant_id, amount, cost=, style_id=, size=, ...)` | `POST /v2/stockx/listings` | basic |
| `stockx.listings.update(listing_id, amount=, currency_code=, expires_at=)` | `PATCH /v2/stockx/listings/{id}` | basic |
| `stockx.listings.list(page_number=, page_size=, listing_statuses=, sku=)` | `GET /v2/stockx/listings` | free |
| `stockx.listings.get(listing_id)` | `GET /v2/stockx/listings/{id}` | free |
| `stockx.listings.get_operation(listing_id, operation_id)` | `GET /v2/stockx/listings/{id}/operations/{op}` | free |
| `stockx.listings.deactivate(listing_id)` | `PUT .../{id}/deactivate` | basic |
| `stockx.listings.activate(listing_id, amount=)` | `PUT .../{id}/activate` | basic |
| `stockx.listings.delete(listing_id, variant_id=)` | `DELETE /v2/stockx/listings/{id}` | basic |
| `stockx.listings.batch_delete(items)` | `POST /v2/stockx/batch/delete-listing` | advanced |
| `stockx.listings.upload(file / rows=, batch_size=)` | `POST /v2/stockx/listings/upload` | advanced |
| `stockx.listings.validate_upload(file / rows=)` | `POST /v2/stockx/listings/upload/validate` | advanced |
| `stockx.listings.upload_status(task_id)` / `wait_for_upload(task_id)` | `GET /v2/stockx/listings/upload/{task_id}` | advanced |
| `stockx.listings.unmatched()` | `GET /v2/stockx/listings/upload/unmatched` | advanced |
| `stockx.listings.unlist(file / rows=)` | `POST /v2/stockx/listings/unlist` | advanced |
| `stockx.listings.unlist_status(task_id)` / `wait_for_unlist(task_id)` | `GET /v2/stockx/listings/unlist/{task_id}` | advanced |
| `stockx.listings.cancel_unlist()` | `POST /v2/stockx/listings/unlist/cancel` | advanced |
| `stockx.listings.clear_all()` | `POST /v2/stockx/listings/clear-all` | advanced |
| `stockx.listings.clear_all_status(task_id)` / `wait_for_clear_all(task_id)` | `GET /v2/stockx/listings/clear-all/{task_id}` | advanced |
| **StockX costs** | | |
| `stockx.costs.set(style_id, size, variant_id, cost)` | `PATCH /v2/stockx/cost` | basic |
| `stockx.costs.list(page=, page_size=, style_id=)` / `iter_list()` | `GET /v2/stockx/costs` | free |
| `stockx.costs.import_csv(file / rows=)` | `POST /v2/stockx/costs/import` | advanced |
| `stockx.costs.update(cost_id, cost=, is_active=)` | `PATCH /v2/stockx/costs/{id}` | basic |
| `stockx.costs.clear()` | `DELETE /v2/stockx/costs` | basic |
| **StockX orders** | | |
| `stockx.orders.sync()` | `POST /v2/stockx/orders/sync` | advanced |
| `stockx.orders.list(page=, page_size=, order_status=, from_date=, to_date=, search=)` / `iter_list()` | `GET /v2/stockx/orders` | advanced |
| `stockx.orders.analytics(from_date=, to_date=, granularity=)` | `GET /v2/stockx/orders/analytics` | advanced |

Methods whose StockX endpoint accepts `connection_id` take it as a keyword argument.

## Examples

Complete, runnable scripts live in [`examples/`](examples/): StockX vs GOAT price comparison, retail-to-StockX arbitrage scan, auto-repricer with a cost floor, bulk CSV listing with progress, sales report with CSV export, and retail restock timelines. [`examples/README.md`](examples/README.md) shows what each one prints (made-up data), for example the price comparison:

```console
$ python examples/01_compare_markets.py DZ5485-612
DZ5485-612  (StockX quotes as of 2026-11-10T14:32:07Z)
  size |   SX ask   SX bid | GOAT ask | cheapest
     9 |      281      240 |      272 | GOAT (-9)
   9.5 |      276      238 |      280 | StockX (-4)
    10 |      268      231 |      275 | StockX (-7)
  10.5 |      271      229 |      262 | GOAT (-9)
```

The snippets below show individual calls.

### Retail inventory

```python
page = client.inventory.search(brand="Nike", limit=20)
print(page["total_skus"], page["has_next_page"])

# every page, lazily
for item in client.inventory.iter_search(style_color="HF1234-100"):
    sku = item["sku"]
    for loc in item["inventory"]:
        print(sku["retailer"], sku["size"], loc["location_code"], loc["stock_level"])

history = client.inventory.history("DICKS", "11943996", hours=24 * 30)
```

### List, reprice, delist on StockX

```python
# by style code + size (backend resolves the variant)
client.stockx.listings.create_by_sku("DZ5485-612", "10", amount=250, cost=180)

# find listing IDs, then reprice
listings = client.stockx.listings.list(sku="DZ5485-612")
client.stockx.listings.update("L-1001", amount=245)

client.stockx.listings.deactivate("L-1001")
client.stockx.listings.activate("L-1001", amount=240)
client.stockx.listings.delete("L-1001", variant_id="1a2b...")  # also drops cost records

client.stockx.listings.batch_delete(["L-1002", ("L-1003", "variant-id")])
```

Prices may be passed as `int`, `float`, `Decimal` or `str`; they are sent as strings (`250.0` → `"250"`).

### Bulk jobs

```python
job = client.stockx.listings.upload("listings.csv", batch_size=50)
# or: upload(rows=[{"sku": "DZ5485-612", "size": "10", "quantity": 1, "amount": 250, "cost": 180}])

final = client.stockx.listings.wait_for_upload(
    job["taskId"],
    poll_interval=5,
    timeout=1800,
    on_progress=lambda s: print(s["status"], s.get("result")),
)
if final["status"] != "SUCCESS":
    print("job ended with", final["status"], final["result"])
print(client.stockx.listings.unmatched()["items"])
```

`wait_for_*` returns once `status` is `SUCCESS`, `FAILURE` or `CANCELLED`, and raises `JobTimeoutError` if `timeout` (seconds) passes first. Without a `timeout` it waits indefinitely.

### Costs and orders

```python
client.stockx.costs.set("DZ5485-612", "10", "1a2b...", 180)
for c in client.stockx.costs.iter_list(style_id="DZ5485"):
    print(c["id"], c["size"], c["cost"])
client.stockx.costs.import_csv("costs.csv")

client.stockx.orders.sync()   # background; there is no status endpoint, query again later
for o in client.stockx.orders.iter_list(order_status="COMPLETED", from_date="2026-01-01"):
    print(o["order_number"], o["total_payout"])
stats = client.stockx.orders.analytics(granularity="weekly")
```

## Multiple StockX accounts

```python
client = Client(connection_id=12)                   # default for every call
client.stockx.listings.list(connection_id=34)       # per-call override
other = client.with_options(connection_id=34)        # shares the connection pool
```

Bulk jobs (CSV upload/unlist, clear all, order sync) always run on the default connection.

## Errors

```python
from solometrics import (
    APIStatusError, NotFoundError, ConflictError, PermissionDeniedError, RateLimitError,
)

try:
    client.stockx.listings.create_by_sku("DZ5485-612", "10", 250, cost=180)
except ConflictError as e:          # keep-listing mode skipped it
    print("skipped:", e.detail)
except NotFoundError:
    print("no such style/size")
except PermissionDeniedError as e:  # not in your StockX plan
    print(e.detail)
except APIStatusError as e:
    print(e.status_code, e.detail, e.body)
```

| Status | Exception |
|---|---|
| 400 | `BadRequestError` |
| 401 | `AuthenticationError` |
| 403 | `PermissionDeniedError` |
| 404 | `NotFoundError` |
| 409 | `ConflictError` |
| 422 | `UnprocessableEntityError` (`.errors` = field list) |
| 429 | `RateLimitError` (`.retry_after`) |
| 502 | `UpstreamError` |
| 504 | `UpstreamTimeoutError` |
| other 5xx | `InternalServerError` |
| network | `APIConnectionError` / `APITimeoutError` |

All inherit from `SolometricsError`.

## Retries and timeouts

By default the client retries twice with exponential backoff (honouring `Retry-After`, capped at 60s):

- **429** — every method (the request was rejected before it ran).
- **502 / 503 / 504, read timeouts, dropped connections** — only `GET`, `PUT`, `PATCH`, `DELETE`. `POST` is not retried, because a create-listing that timed out at the gateway may already have been placed on StockX.
- **Connection refused / DNS failures** — every method.

```python
client = Client(max_retries=5, timeout=30)
client.with_options(max_retries=0).stockx.listings.list()
```

## Custom HTTP client

```python
import httpx
client = Client(http_client=httpx.Client(proxy="http://127.0.0.1:8080", timeout=30))
```

## Endpoints not wrapped yet

```python
client.get("/v2/stockx/some/new/endpoint", params={"x": 1})
client.post("/v2/...", json={...})
```

## Development

```bash
uv sync
uv run pytest
python scripts/gen_async.py   # after editing src/solometrics/_resources.py
```

`_async_resources.py` is generated from `_resources.py`; edit the sync file and regenerate. `python scripts/gen_async.py --check` fails if they are out of sync.

## Releasing

1. Bump `__version__` in `src/solometrics/_version.py` and merge to `main`.
2. Tag and push: `git tag v0.1.1 && git push origin v0.1.1`.

The **Release** workflow runs CI, checks the tag matches `_version.py`, builds the sdist and wheel, publishes to PyPI (trusted publishing, no token), and creates a GitHub release with the built files.

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

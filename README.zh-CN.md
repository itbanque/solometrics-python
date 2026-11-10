# solometrics — SneakersRadar API Python SDK

[English](https://github.com/itbanque/solometrics-python/blob/main/README.md) | **简体中文**

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

[SneakersRadar API](https://www.sneakers.itbanque.com/docs) 的 Python 客户端：零售商库存与 SKU 历史、StockX / GOAT 行情报价，以及 StockX 挂单、成本和订单管理。

- 同步 `Client` 和异步 `AsyncClient`，方法完全一致
- 响应带类型（`TypedDict`），运行时就是普通 `dict`
- 按状态码区分的异常类型（`NotFoundError`、`RateLimitError` 等）
- 自动重试，指数退避，遵守 `Retry-After`
- 自动翻页（`iter_*`）和后台任务轮询（`wait_for_*`）
- CSV 上传支持文件路径、bytes、文件对象或 dict 列表
- 运行时只依赖 `httpx`

需要 Python 3.9+。

## 安装

```bash
pip install solometrics
# 或从源码安装
pip install git+https://github.com/itbanque/solometrics-python
```

## 快速开始

在 <https://www.sneakers.itbanque.com/account> → **API Keys** 生成 key。

```python
from solometrics import Client

client = Client(api_key="sr_live_...")  # 或设置环境变量 SOLOMETRICS_API_KEY

quotes = client.stockx.market.search("DZ5485-612")
for v in quotes["variants"]:
    print(v["size"], v["lowestAsk"], v["highestBid"])
```

异步：

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

## 接口对照表

| SDK 方法 | HTTP | 套餐 |
|---|---|---|
| **零售数据** | | |
| `inventory.search(q=, style_color=, brand=, retailer=, size=, retailer_sku=, supplier_sku=, limit=, offset=)` | `GET /v1/inventory/search` | data |
| `inventory.iter_search(...)` | 自动翻页（同上） | data |
| `inventory.history(retailer, retailer_sku, hours=)` | `GET /v1/reporting/retailers/{retailer}/skus/{sku}/history` | data |
| **行情数据** | | |
| `stockx.market.search(style_id, size=, force=)` | `GET /v2/stockx/market/search` | |
| `stockx.market.hot(limit=, page=)` / `iter_hot()` | `GET /v2/stockx/market/hot` | |
| `stockx.market.variant(product_id, variant_id, currency_code=)` | `GET /v2/stockx/catalog/products/{p}/variants/{v}/market-data` | free |
| `goat.market.search(style_id)` | `GET /v2/goat/market/search` | |
| **StockX 商品目录** | | |
| `stockx.catalog.search(q, page_number=, page_size=)` | `GET /v2/stockx/catalog/search` | free |
| `stockx.catalog.variants(product_id, style_id=)` | `GET /v2/stockx/catalog/products/{p}/variants` | free |
| **StockX 挂单** | | |
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
| **StockX 成本** | | |
| `stockx.costs.set(style_id, size, variant_id, cost)` | `PATCH /v2/stockx/cost` | basic |
| `stockx.costs.list(page=, page_size=, style_id=)` / `iter_list()` | `GET /v2/stockx/costs` | free |
| `stockx.costs.import_csv(file / rows=)` | `POST /v2/stockx/costs/import` | advanced |
| `stockx.costs.update(cost_id, cost=, is_active=)` | `PATCH /v2/stockx/costs/{id}` | basic |
| `stockx.costs.clear()` | `DELETE /v2/stockx/costs` | basic |
| **StockX 订单** | | |
| `stockx.orders.sync()` | `POST /v2/stockx/orders/sync` | advanced |
| `stockx.orders.list(page=, page_size=, order_status=, from_date=, to_date=, search=)` / `iter_list()` | `GET /v2/stockx/orders` | advanced |
| `stockx.orders.analytics(from_date=, to_date=, granularity=)` | `GET /v2/stockx/orders/analytics` | advanced |

StockX 接口中支持 `connection_id` 的方法，都可以通过关键字参数传入。最后一列是所需套餐（plan）。

## 示例

[`examples/`](examples/README.zh-CN.md) 里有可以直接运行的完整脚本：StockX 与 GOAT 分尺码比价、零售转 StockX 套利扫描、带成本底价的自动改价、CSV 批量挂单（带进度）、销售报表（可导出 CSV）、零售补货时间线。[`examples/README.zh-CN.md`](examples/README.zh-CN.md) 展示了每个脚本的输出（示例数据），比如比价脚本：

```console
$ python examples/01_compare_markets.py DZ5485-612
DZ5485-612  (StockX quotes as of 2026-11-10T14:32:07Z)
  size |   SX ask   SX bid | GOAT ask | cheapest
     9 |      281      240 |      272 | GOAT (-9)
   9.5 |      276      238 |      280 | StockX (-4)
    10 |      268      231 |      275 | StockX (-7)
  10.5 |      271      229 |      262 | GOAT (-9)
```

下面是单个调用的代码片段。

### 零售库存

```python
page = client.inventory.search(brand="Nike", limit=20)
print(page["total_skus"], page["has_next_page"])

# 逐页惰性遍历所有结果
for item in client.inventory.iter_search(style_color="HF1234-100"):
    sku = item["sku"]
    for loc in item["inventory"]:
        print(sku["retailer"], sku["size"], loc["location_code"], loc["stock_level"])

history = client.inventory.history("DICKS", "11943996", hours=24 * 30)
```

### 在 StockX 上挂单、改价、下架

```python
# 按款号 + 尺码挂单（后端自动匹配 variant）
client.stockx.listings.create_by_sku("DZ5485-612", "10", amount=250, cost=180)

# 查到 listing ID 后改价
listings = client.stockx.listings.list(sku="DZ5485-612")
client.stockx.listings.update("L-1001", amount=245)

client.stockx.listings.deactivate("L-1001")
client.stockx.listings.activate("L-1001", amount=240)
client.stockx.listings.delete("L-1001", variant_id="1a2b...")  # 同时删除成本记录

client.stockx.listings.batch_delete(["L-1002", ("L-1003", "variant-id")])
```

价格可以传 `int`、`float`、`Decimal` 或 `str`，发送时统一转成字符串（`250.0` → `"250"`）。

### 批量任务

```python
job = client.stockx.listings.upload("listings.csv", batch_size=50)
# 或者：upload(rows=[{"sku": "DZ5485-612", "size": "10", "quantity": 1, "amount": 250, "cost": 180}])

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

`wait_for_*` 在 `status` 变为 `SUCCESS`、`FAILURE` 或 `CANCELLED` 时返回；如果先超过 `timeout`（秒），抛出 `JobTimeoutError`。不传 `timeout` 则一直等待。

### 成本和订单

```python
client.stockx.costs.set("DZ5485-612", "10", "1a2b...", 180)
for c in client.stockx.costs.iter_list(style_id="DZ5485"):
    print(c["id"], c["size"], c["cost"])
client.stockx.costs.import_csv("costs.csv")

client.stockx.orders.sync()   # 后台执行，没有状态查询接口，稍后再查订单即可
for o in client.stockx.orders.iter_list(order_status="COMPLETED", from_date="2026-01-01"):
    print(o["order_number"], o["total_payout"])
stats = client.stockx.orders.analytics(granularity="weekly")
```

## 多个 StockX 账户

```python
client = Client(connection_id=12)                   # 所有调用的默认账户
client.stockx.listings.list(connection_id=34)       # 单次调用覆盖
other = client.with_options(connection_id=34)        # 共享连接池
```

批量任务（CSV 上传/下架、全部清空、订单同步）始终使用默认账户。

## 错误处理

```python
from solometrics import (
    APIStatusError, NotFoundError, ConflictError, PermissionDeniedError, RateLimitError,
)

try:
    client.stockx.listings.create_by_sku("DZ5485-612", "10", 250, cost=180)
except ConflictError as e:          # keep-listing 模式跳过了这一单
    print("skipped:", e.detail)
except NotFoundError:
    print("no such style/size")
except PermissionDeniedError as e:  # 不在你的 StockX 套餐内
    print(e.detail)
except APIStatusError as e:
    print(e.status_code, e.detail, e.body)
```

| 状态码 | 异常 |
|---|---|
| 400 | `BadRequestError` |
| 401 | `AuthenticationError` |
| 403 | `PermissionDeniedError` |
| 404 | `NotFoundError` |
| 409 | `ConflictError` |
| 422 | `UnprocessableEntityError`（`.errors` 为字段错误列表） |
| 429 | `RateLimitError`（`.retry_after`） |
| 502 | `UpstreamError` |
| 504 | `UpstreamTimeoutError` |
| 其他 5xx | `InternalServerError` |
| 网络错误 | `APIConnectionError` / `APITimeoutError` |

所有异常都继承自 `SolometricsError`。

## 重试和超时

默认重试两次，指数退避（遵守 `Retry-After`，最长 60 秒）：

- **429**：所有方法都重试（请求在执行前就被拒绝了）。
- **502 / 503 / 504、读超时、连接中断**：只重试 `GET`、`PUT`、`PATCH`、`DELETE`。`POST` 不重试，因为在网关超时的挂单请求可能已经在 StockX 上生效了。
- **连接被拒 / DNS 失败**：所有方法都重试。

```python
client = Client(max_retries=5, timeout=30)
client.with_options(max_retries=0).stockx.listings.list()
```

## 自定义 HTTP 客户端

```python
import httpx
client = Client(http_client=httpx.Client(proxy="http://127.0.0.1:8080", timeout=30))
```

## 尚未封装的接口

```python
client.get("/v2/stockx/some/new/endpoint", params={"x": 1})
client.post("/v2/...", json={...})
```

## 开发

```bash
uv sync
uv run pytest
python scripts/gen_async.py   # 修改 src/solometrics/_resources.py 之后运行
```

`_async_resources.py` 由 `_resources.py` 生成：先改同步文件，再重新生成。`python scripts/gen_async.py --check` 会在两者不一致时报错。

## 发布

1. 修改 `src/solometrics/_version.py` 里的 `__version__` 并合并到 `main`。
2. 打 tag 并推送：`git tag v0.1.1 && git push origin v0.1.1`。

**Release** workflow 会运行 CI、检查 tag 与 `_version.py` 一致、构建 sdist 和 wheel、发布到 PyPI（trusted publishing，不需要 token），并创建附带构建产物的 GitHub release。

## 许可证

Apache License 2.0，见 [LICENSE](LICENSE) 和 [NOTICE](NOTICE)。

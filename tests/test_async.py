from __future__ import annotations

import httpx
import pytest

import solometrics
from solometrics import AsyncClient

from .conftest import Recorder


async def test_async_search(aclient: AsyncClient, rec: Recorder) -> None:
    rec.handler = lambda r: httpx.Response(200, json={"platform": "stockx", "variants": [{"size": "10"}]})
    out = await aclient.stockx.market.search("DZ5485-612")
    assert out["variants"][0]["size"] == "10"
    assert rec.last.headers["X-API-Key"] == "sr_live_test"


async def test_async_iter_search(aclient: AsyncClient, rec: Recorder) -> None:
    pages = {
        "0": {"items": [{"sku": {"id": 1}}], "has_next_page": True},
        "1": {"items": [{"sku": {"id": 2}}], "has_next_page": False},
    }
    rec.handler = lambda r: httpx.Response(200, json=pages[r.url.params["offset"]])
    ids = [it["sku"]["id"] async for it in aclient.inventory.iter_search(page_size=1)]
    assert ids == [1, 2]


async def test_async_wait_with_async_callback(aclient: AsyncClient, rec: Recorder) -> None:
    statuses = iter(["PENDING", "FAILURE"])
    rec.handler = lambda r: httpx.Response(200, json={"taskId": "t", "status": next(statuses)})
    seen = []

    async def cb(s):
        seen.append(s["status"])

    final = await aclient.stockx.listings.wait_for_unlist("t", poll_interval=0, on_progress=cb)
    assert final["status"] == "FAILURE"
    assert seen == ["PENDING", "FAILURE"]


async def test_async_retry_and_errors(aclient: AsyncClient, rec: Recorder) -> None:
    rec.handler = lambda r: httpx.Response(429, json={"detail": "Too Many Requests"})
    with pytest.raises(solometrics.RateLimitError):
        await aclient.stockx.costs.list()
    assert len(rec.requests) == 3


async def test_async_context_manager(rec: Recorder) -> None:
    async with AsyncClient(
        "k", base_url="https://api.test", http_client=httpx.AsyncClient(transport=httpx.MockTransport(rec))
    ) as c:
        await c.stockx.orders.sync()
    assert rec.last.method == "POST"
    assert rec.last.url.path == "/v2/stockx/orders/sync"

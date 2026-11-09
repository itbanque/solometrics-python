from __future__ import annotations

import json
from typing import Any, Callable, List

import httpx
import pytest

from solometrics import AsyncClient, Client

BASE = "https://api.test"


class Recorder:
    """Collects requests and answers them with a user-supplied handler."""

    def __init__(self) -> None:
        self.requests: List[httpx.Request] = []
        self.handler: Callable[[httpx.Request], httpx.Response] = lambda r: httpx.Response(200, json={})

    def __call__(self, request: httpx.Request) -> httpx.Response:
        request.read()
        self.requests.append(request)
        return self.handler(request)

    @property
    def last(self) -> httpx.Request:
        return self.requests[-1]

    def last_json(self) -> Any:
        return json.loads(self.last.content)


@pytest.fixture
def rec() -> Recorder:
    return Recorder()


@pytest.fixture
def client(rec: Recorder, monkeypatch: pytest.MonkeyPatch) -> Client:
    monkeypatch.setattr("solometrics._client.time.sleep", lambda s: None)
    http = httpx.Client(transport=httpx.MockTransport(rec))
    return Client("sr_live_test", base_url=BASE, http_client=http)


@pytest.fixture
def aclient(rec: Recorder, monkeypatch: pytest.MonkeyPatch) -> AsyncClient:
    async def _nosleep(_: float) -> None:
        return None

    monkeypatch.setattr("solometrics._async_client.asyncio.sleep", _nosleep)
    monkeypatch.setattr("solometrics._async_resources.asyncio.sleep", _nosleep)
    http = httpx.AsyncClient(transport=httpx.MockTransport(rec))
    return AsyncClient("sr_live_test", base_url=BASE, http_client=http)

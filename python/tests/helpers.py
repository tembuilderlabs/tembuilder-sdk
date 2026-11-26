from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from tembuilder import AsyncTembuilder, Tembuilder

CONTRACT_DIR = Path(__file__).resolve().parents[2] / "contract"

Handler = Callable[[httpx.Request], httpx.Response]


def load_contract(name: str) -> Any:
    return json.loads((CONTRACT_DIR / name).read_text())


class Recorder:
    """A MockTransport handler that records requests and answers from a queue (last one repeats)."""

    def __init__(self, *handlers: Handler) -> None:
        self.handlers = handlers
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        request.read()
        self.requests.append(request)
        handler = self.handlers[min(len(self.requests) - 1, len(self.handlers) - 1)]
        return handler(request)


def json_response(status: int, body: Any, headers: dict[str, str] | None = None) -> Handler:
    return lambda _request: httpx.Response(status, json=body, headers=headers)


def make_client(recorder: Recorder, **options: Any) -> Tembuilder:
    defaults: dict[str, Any] = {"api_key": "test-key", "base_url": "https://api.test", "max_retries": 0}
    return Tembuilder(transport=httpx.MockTransport(recorder), **{**defaults, **options})


def make_async_client(recorder: Recorder, **options: Any) -> AsyncTembuilder:
    defaults: dict[str, Any] = {"api_key": "test-key", "base_url": "https://api.test", "max_retries": 0}
    return AsyncTembuilder(transport=httpx.MockTransport(recorder), **{**defaults, **options})

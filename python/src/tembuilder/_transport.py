"""httpx transports adding bounded, jittered retries of transient failures.

A request is resent only when that is safe: GETs after any transient failure,
and other methods only on 429/503, which mean the request was not processed
(the render endpoint answers 503 before admitting a job). A POST that failed
without a response is never resent, because it may have been accepted.
"""

from __future__ import annotations

import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

import anyio
import httpx

from ._errors import parse_retry_after

RETRYABLE_STATUSES = frozenset({429, 503})
RETRYABLE_GET_STATUSES = frozenset({429, 502, 503, 504})


@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int = 2
    base_delay: float = 0.5
    max_delay: float = 8.0
    random: Callable[[], float] = field(default=random.random)

    def delay(self, attempt: int, retry_after: int | None) -> float:
        """Server Retry-After wins (capped); otherwise exponential backoff with full jitter."""
        if retry_after is not None:
            return float(min(retry_after, self.max_delay))
        return self.random() * min(self.base_delay * 2.0**attempt, self.max_delay)


def _idempotent(request: httpx.Request) -> bool:
    return request.method in ("GET", "HEAD")


def _retryable_status(request: httpx.Request, response: httpx.Response) -> bool:
    allowed = RETRYABLE_GET_STATUSES if _idempotent(request) else RETRYABLE_STATUSES
    return response.status_code in allowed


class RetryTransport(httpx.BaseTransport):
    def __init__(
        self,
        inner: httpx.BaseTransport,
        policy: RetryPolicy,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._inner = inner
        self._policy = policy
        self._sleep = sleep

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        attempt = 0
        while True:
            can_retry = attempt < self._policy.max_retries
            try:
                response = self._inner.handle_request(request)
            except httpx.TransportError:
                if can_retry and _idempotent(request):
                    self._sleep(self._policy.delay(attempt, None))
                    attempt += 1
                    continue
                raise
            if can_retry and _retryable_status(request, response):
                retry_after = parse_retry_after(response.headers.get("retry-after"))
                response.close()
                self._sleep(self._policy.delay(attempt, retry_after))
                attempt += 1
                continue
            return response

    def close(self) -> None:
        self._inner.close()


class AsyncRetryTransport(httpx.AsyncBaseTransport):
    def __init__(
        self,
        inner: httpx.AsyncBaseTransport,
        policy: RetryPolicy,
        sleep: Callable[[float], Awaitable[None]] = anyio.sleep,
    ) -> None:
        self._inner = inner
        self._policy = policy
        self._sleep = sleep

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        attempt = 0
        while True:
            can_retry = attempt < self._policy.max_retries
            try:
                response = await self._inner.handle_async_request(request)
            except httpx.TransportError:
                if can_retry and _idempotent(request):
                    await self._sleep(self._policy.delay(attempt, None))
                    attempt += 1
                    continue
                raise
            if can_retry and _retryable_status(request, response):
                retry_after = parse_retry_after(response.headers.get("retry-after"))
                await response.aclose()
                await self._sleep(self._policy.delay(attempt, retry_after))
                attempt += 1
                continue
            return response

    async def aclose(self) -> None:
        await self._inner.aclose()

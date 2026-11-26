from __future__ import annotations

import httpx
import pytest
from helpers import Recorder, json_response, make_async_client, make_client

from tembuilder import APIError, ConnectionError, RetryPolicy, TimeoutError

OK = json_response(
    200,
    {
        "api_key_id": "6f1d2c1e-7a55-4c0e-9a0e-3a1f1b2c3d4e",
        "workspace_id": "0c8a1d4f-2b3c-4d5e-8f90-a1b2c3d4e5f6",
        "project": {"id": "9b2e7c1a-3d4f-4a5b-8c6d-7e8f9a0b1c2d", "name": "B", "slug": "b"},
        "scopes": [],
    },
)
BUSY = json_response(503, {"code": "COMMON_UNAVAILABLE", "description": "busy", "details": []})
QUEUED = json_response(
    202, {"render_id": "5a6b7c8d-1e2f-4a3b-8c4d-5e6f7a8b9c0d", "status": "queued", "status_url": "/v1/renders/x"}
)
TEMPLATE = "7d0f5a2e-1c3b-4d5e-9f80-a1b2c3d4e5f6"
FAST = {"max_retries": 2, "retry_base_delay": 0.001, "max_retry_delay": 0.002}


def raise_(error: Exception):  # type: ignore[no-untyped-def]
    def handler(request: httpx.Request) -> httpx.Response:
        raise error

    return handler


@pytest.mark.parametrize("status", [429, 502, 503, 504])
def test_get_retries_transient_statuses(status: int) -> None:
    recorder = Recorder(json_response(status, {}), OK)
    make_client(recorder, **FAST).account.get()
    assert len(recorder.requests) == 2


def test_retry_after_is_capped() -> None:
    recorder = Recorder(json_response(503, {}, {"retry-after": "120"}), OK)
    make_client(recorder, **FAST).account.get()
    assert len(recorder.requests) == 2


def test_post_resent_after_503_with_same_body() -> None:
    recorder = Recorder(BUSY, QUEUED)
    make_client(recorder, **FAST).renders.create(TEMPLATE, parameters={"a": 1})
    assert len(recorder.requests) == 2
    assert recorder.requests[1].content == recorder.requests[0].content


def test_post_not_resent_after_502() -> None:
    recorder = Recorder(json_response(502, {}))
    with pytest.raises(APIError):
        make_client(recorder, **FAST).renders.create(TEMPLATE)
    assert len(recorder.requests) == 1


def test_returns_last_response_when_exhausted() -> None:
    recorder = Recorder(BUSY)
    with pytest.raises(APIError) as caught:
        make_client(recorder, **FAST).account.get()
    assert caught.value.code == "COMMON_UNAVAILABLE"
    assert len(recorder.requests) == 3


def test_get_retried_after_network_error() -> None:
    recorder = Recorder(raise_(httpx.ConnectError("reset")), OK)
    make_client(recorder, **FAST).account.get()
    assert len(recorder.requests) == 2


def test_post_not_resent_after_network_error() -> None:
    recorder = Recorder(raise_(httpx.ConnectError("reset")))
    with pytest.raises(ConnectionError, match="reset"):
        make_client(recorder, **FAST).renders.create(TEMPLATE)
    assert len(recorder.requests) == 1


def test_timeout_is_translated() -> None:
    recorder = Recorder(raise_(httpx.ReadTimeout("slow")))
    with pytest.raises(TimeoutError):
        make_client(recorder).account.get()


@pytest.mark.anyio
async def test_async_retries_and_translations() -> None:
    recorder = Recorder(BUSY, OK)
    client = make_async_client(recorder, **FAST)
    await client.account.get()
    assert len(recorder.requests) == 2

    recorder = Recorder(raise_(httpx.ConnectError("reset")), OK)
    await make_async_client(recorder, **FAST).account.get()
    assert len(recorder.requests) == 2

    recorder = Recorder(raise_(httpx.ConnectError("reset")))
    with pytest.raises(ConnectionError):
        await make_async_client(recorder, **FAST).renders.create(TEMPLATE)
    assert len(recorder.requests) == 1

    recorder = Recorder(raise_(httpx.ConnectTimeout("slow")))
    with pytest.raises(TimeoutError):
        await make_async_client(recorder).account.get()

    recorder = Recorder(BUSY)
    with pytest.raises(APIError):
        await make_async_client(recorder, **FAST).account.get()
    assert len(recorder.requests) == 3


def test_policy_delay() -> None:
    policy = RetryPolicy(max_retries=5, base_delay=0.1, max_delay=1.0, random=lambda: 0.5)
    assert policy.delay(0, None) == pytest.approx(0.05)
    assert policy.delay(10, None) == pytest.approx(0.5)
    assert policy.delay(0, 0) == 0.0
    assert policy.delay(0, 30) == 1.0
    assert 0 <= RetryPolicy().delay(0, None) <= 0.5

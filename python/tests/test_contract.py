"""Replays the language-neutral cases in contract/cases.json (shared by every SDK)."""

from __future__ import annotations

import base64
import datetime
import json
from typing import Any

import httpx
import pytest
from helpers import Recorder, load_contract, make_async_client, make_client

from tembuilder import APIError, AsyncTembuilder, RenderFile, Tembuilder

SUITE = load_contract("cases.json")
DATE_PARAMS = {"started_after", "started_before"}


def _kwargs(args: dict[str, Any]) -> dict[str, Any]:
    return {key: datetime.datetime.fromisoformat(value) if key in DATE_PARAMS else value for key, value in args.items()}


def call(client: Tembuilder, operation: str, args: dict[str, Any]) -> Any:
    kwargs = _kwargs(args)
    if operation == "getAccount":
        return client.account.get()
    if operation == "listTemplates":
        return client.templates.list(**kwargs)
    if operation == "getTemplate":
        return client.templates.get(kwargs.pop("template_id"), **kwargs)
    if operation == "createRender":
        request = dict(kwargs["request"])
        return client.renders.create(request.pop("template_id"), **request)
    if operation == "listRenders":
        return client.renders.list(**kwargs)
    if operation == "getRender":
        return client.renders.get(kwargs["render_id"])
    if operation == "downloadRender":
        return client.renders.download(kwargs["render_id"])
    raise AssertionError(f"unknown contract operation {operation}")


async def acall(client: AsyncTembuilder, operation: str, args: dict[str, Any]) -> Any:
    kwargs = _kwargs(args)
    if operation == "getAccount":
        return await client.account.get()
    if operation == "listTemplates":
        return await client.templates.list(**kwargs)
    if operation == "getTemplate":
        return await client.templates.get(kwargs.pop("template_id"), **kwargs)
    if operation == "createRender":
        request = dict(kwargs["request"])
        return await client.renders.create(request.pop("template_id"), **request)
    if operation == "listRenders":
        return await client.renders.list(**kwargs)
    if operation == "getRender":
        return await client.renders.get(kwargs["render_id"])
    if operation == "downloadRender":
        return await client.renders.download(kwargs["render_id"])
    raise AssertionError(f"unknown contract operation {operation}")


def normalize(value: Any) -> Any:
    """Compares timestamps by instant: models serialize UTC as +00:00, the API sends Z."""
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, str) and len(value) >= 20 and value[10:11] == "T":
        return datetime.datetime.fromisoformat(value)
    return value


def stub(response: dict[str, Any]) -> httpx.Response:
    if "bodyBase64" in response:
        content = base64.b64decode(response["bodyBase64"])
    elif "text" in response:
        content = response["text"].encode()
    else:
        content = json.dumps(response["body"]).encode()
    return httpx.Response(response["status"], content=content, headers=response["headers"])


def check_request(case: dict[str, Any], recorder: Recorder) -> None:
    assert len(recorder.requests) == 1
    sent = recorder.requests[0]
    expected = case["request"]
    assert sent.method == expected["method"]
    assert sent.url.path == expected["path"]
    query = dict(sent.url.params)
    for key in DATE_PARAMS & query.keys():
        assert datetime.datetime.fromisoformat(query.pop(key)) == datetime.datetime.fromisoformat(
            expected["query"][key]
        )
    assert query == {k: v for k, v in expected["query"].items() if k not in DATE_PARAMS}
    assert sent.headers["apikey"] == SUITE["api_key"]
    if expected["body"] is None:
        assert sent.content == b""
    else:
        assert json.loads(sent.content) == expected["body"]


def check_outcome(case: dict[str, Any], value: Any, error: BaseException | None) -> None:
    expect = case["expect"]
    if "error" in expect:
        assert isinstance(error, APIError)
        assert error.status == expect["error"]["status"]
        assert error.code == expect["error"]["code"]
        return
    assert error is None
    if "file" in expect:
        assert isinstance(value, RenderFile)
        assert base64.b64encode(value.content).decode() == expect["file"]["base64"]
        assert value.filename == expect["file"]["filename"]
        assert value.content_type == expect["file"]["content_type"]
        return
    assert normalize(value.to_dict()) == normalize(case["response"]["body"])


CASES = [pytest.param(case, id=case["name"]) for case in SUITE["cases"]]


@pytest.mark.parametrize("case", CASES)
def test_contract_sync(case: dict[str, Any]) -> None:
    recorder = Recorder(lambda _request: stub(case["response"]))
    value: Any = None
    error: BaseException | None = None
    with make_client(recorder, api_key=SUITE["api_key"]) as client:
        try:
            value = call(client, case["operation"], case["args"])
        except APIError as raised:
            error = raised
    check_request(case, recorder)
    check_outcome(case, value, error)


@pytest.mark.anyio
@pytest.mark.parametrize("case", CASES)
async def test_contract_async(case: dict[str, Any]) -> None:
    recorder = Recorder(lambda _request: stub(case["response"]))
    value: Any = None
    error: BaseException | None = None
    async with make_async_client(recorder, api_key=SUITE["api_key"]) as client:
        try:
            value = await acall(client, case["operation"], case["args"])
        except APIError as raised:
            error = raised
    check_request(case, recorder)
    check_outcome(case, value, error)


def test_runner_rejects_unknown_operation() -> None:
    with pytest.raises(AssertionError, match="unknown contract operation"):
        call(make_client(Recorder()), "nope", {})


@pytest.mark.anyio
async def test_async_runner_rejects_unknown_operation() -> None:
    with pytest.raises(AssertionError, match="unknown contract operation"):
        await acall(make_async_client(Recorder()), "nope", {})

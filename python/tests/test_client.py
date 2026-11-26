from __future__ import annotations

from typing import Any

import httpx
import pytest
from helpers import Recorder, json_response, make_async_client, make_client

from tembuilder import (
    DEFAULT_BASE_URL,
    APIError,
    AsyncTembuilder,
    RenderFailedError,
    RenderTimeoutError,
    Tembuilder,
    TembuilderError,
    __version__,
    filename_from_disposition,
)

RENDER = "5a6b7c8d-1e2f-4a3b-8c4d-5e6f7a8b9c0d"
TEMPLATE = "7d0f5a2e-1c3b-4d5e-9f80-a1b2c3d4e5f6"
ACCOUNT = {
    "api_key_id": RENDER,
    "workspace_id": RENDER,
    "project": {"id": RENDER, "name": "B", "slug": "b"},
    "scopes": [],
}
NOT_FOUND = json_response(404, {"code": "RENDER_NOT_FOUND", "description": "render not found", "details": []})
QUEUED = json_response(202, {"render_id": RENDER, "status": "queued", "status_url": f"/v1/renders/{RENDER}"})


def status(value: str, **extra: Any):  # type: ignore[no-untyped-def]
    return json_response(200, {"render_id": RENDER, "status": value, **extra})


def template(identifier: str) -> dict[str, Any]:
    return {
        "id": TEMPLATE,
        "slug": identifier,
        "name": "T",
        "current_version": 1,
        "status": "published",
        "published_versions": [1],
        "created_at": None,
        "updated_at": None,
    }


def render(identifier: str) -> dict[str, Any]:
    return {
        "id": RENDER,
        "short_id": identifier,
        "status": "success",
        "template_id": TEMPLATE,
        "template_version": 1,
        "variant": None,
        "duration_ms": None,
        "error_message": None,
        "started_at": "2026-11-20T08:30:00Z",
        "completed_at": None,
        "status_url": "/s",
        "download_url": None,
    }


class TestConfiguration:
    def test_requires_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("TEMBUILDER_API_KEY", raising=False)
        with pytest.raises(TembuilderError, match="API key is required"):
            Tembuilder()

    def test_reads_environment_and_sends_identity_headers(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEMBUILDER_API_KEY", "env-key")
        monkeypatch.setenv("TEMBUILDER_BASE_URL", "https://staging.test//")
        recorder = Recorder(json_response(200, ACCOUNT))
        with Tembuilder(transport=httpx.MockTransport(recorder)) as client:
            client.account.get()
        sent = recorder.requests[0]
        assert str(sent.url) == "https://staging.test/v1/me"
        assert sent.headers["apikey"] == "env-key"
        assert sent.headers["user-agent"] == f"tembuilder-python/{__version__}"

    def test_defaults_to_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("TEMBUILDER_BASE_URL", raising=False)
        recorder = Recorder(json_response(200, ACCOUNT))
        Tembuilder(api_key="k", transport=httpx.MockTransport(recorder)).account.get()
        assert str(recorder.requests[0].url) == f"{DEFAULT_BASE_URL}/v1/me"

    def test_default_transports_are_constructed(self) -> None:
        Tembuilder(api_key="k").close()

    @pytest.mark.anyio
    async def test_async_default_transport_and_context_manager(self) -> None:
        async with AsyncTembuilder(api_key="k"):
            pass

    def test_undocumented_success_status_is_reported(self) -> None:
        recorder = Recorder(lambda _r: httpx.Response(204))
        with pytest.raises(TembuilderError, match="unexpected response body for HTTP 204"):
            make_client(recorder).account.get()


class TestPagination:
    def test_templates_list_all(self) -> None:
        recorder = Recorder(
            json_response(200, {"data": [template("a"), template("b")], "page": 1, "per_page": 2, "has_more": True}),
            json_response(200, {"data": [template("c")], "page": 2, "per_page": 2, "has_more": False}),
        )
        slugs = [t.slug for t in make_client(recorder).templates.list_all(status="published", per_page=2)]
        assert slugs == ["a", "b", "c"]
        assert [r.url.params["page"] for r in recorder.requests] == ["1", "2"]

    def test_renders_list_all(self) -> None:
        recorder = Recorder(
            json_response(200, {"data": [render("a")], "page": 1, "per_page": 1, "has_more": True}),
            json_response(200, {"data": [render("b")], "page": 2, "per_page": 1, "has_more": False}),
        )
        assert [r.short_id for r in make_client(recorder).renders.list_all(template_id=TEMPLATE)] == ["a", "b"]

    @pytest.mark.anyio
    async def test_async_list_all(self) -> None:
        recorder = Recorder(
            json_response(200, {"data": [template("a")], "page": 1, "per_page": 1, "has_more": True}),
            json_response(200, {"data": [template("b")], "page": 2, "per_page": 1, "has_more": False}),
        )
        assert [t.slug async for t in make_async_client(recorder).templates.list_all()] == ["a", "b"]
        recorder = Recorder(
            json_response(200, {"data": [render("a")], "page": 1, "per_page": 1, "has_more": True}),
            json_response(200, {"data": [render("b")], "page": 2, "per_page": 1, "has_more": False}),
        )
        assert [r.short_id async for r in make_async_client(recorder).renders.list_all()] == ["a", "b"]


class TestDownload:
    def test_defaults_without_headers(self) -> None:
        response = httpx.Response(200, content=b"%P")
        del response.headers["content-length"]
        recorder = Recorder(lambda _r: response)
        file = make_client(recorder).renders.download(RENDER)
        assert (file.content, file.content_type, file.filename) == (b"%P", "application/pdf", None)


class TestWait:
    def test_tolerates_early_404_then_polls_until_success(self) -> None:
        recorder = Recorder(NOT_FOUND, status("pending"), status("success"))
        result = make_client(recorder).renders.wait_for(RENDER, poll_interval=0.001)
        assert result.status == "success"
        assert len(recorder.requests) == 3

    def test_create_and_wait(self) -> None:
        recorder = Recorder(QUEUED, status("success"))
        assert make_client(recorder).renders.create_and_wait(TEMPLATE, version=1).status == "success"
        assert recorder.requests[0].method == "POST"

    @pytest.mark.parametrize("terminal", ["failed", "quota_exceeded"])
    def test_terminal_failures(self, terminal: str) -> None:
        recorder = Recorder(status(terminal, error_message="boom"))
        with pytest.raises(RenderFailedError, match="boom") as caught:
            make_client(recorder).renders.wait_for(RENDER)
        assert caught.value.render.status == terminal

    def test_timeout_keeps_last_status(self) -> None:
        recorder = Recorder(status("pending"))
        with pytest.raises(RenderTimeoutError) as caught:
            make_client(recorder).renders.wait_for(RENDER, poll_interval=0.001, timeout=0.01)
        assert caught.value.last_status is not None
        assert caught.value.last_status.status == "pending"
        assert caught.value.render_id == RENDER

    def test_404_after_grace_or_after_a_status_is_an_error(self) -> None:
        with pytest.raises(APIError):
            make_client(Recorder(NOT_FOUND)).renders.wait_for(RENDER, not_found_grace=0)
        with pytest.raises(APIError):
            make_client(Recorder(status("pending"), NOT_FOUND)).renders.wait_for(RENDER, poll_interval=0.001)

    def test_other_errors_propagate(self) -> None:
        recorder = Recorder(json_response(403, {"code": "COMMON_FORBIDDEN", "description": "no", "details": []}))
        with pytest.raises(APIError) as caught:
            make_client(recorder).renders.wait_for(RENDER)
        assert caught.value.status == 403

    @pytest.mark.anyio
    async def test_async_wait_paths(self) -> None:
        recorder = Recorder(QUEUED, NOT_FOUND, status("pending"), status("success"))
        result = await make_async_client(recorder).renders.create_and_wait(TEMPLATE, poll_interval=0.001)
        assert result.status == "success"
        with pytest.raises(RenderFailedError):
            await make_async_client(Recorder(status("failed"))).renders.wait_for(RENDER)
        with pytest.raises(RenderTimeoutError):
            await make_async_client(Recorder(status("pending"))).renders.wait_for(
                RENDER, poll_interval=0.001, timeout=0.01
            )


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (None, None),
        ("inline", None),
        ('attachment; filename="report.pdf"', "report.pdf"),
        ("attachment; filename=plain.pdf; size=3", "plain.pdf"),
        ("attachment; filename*=UTF-8''h%C3%B3a-%C4%91%C6%A1n.pdf", "hóa-đơn.pdf"),
        ("attachment; filename*=utf-8''bad%E0%A4.pdf", "bad%E0%A4.pdf"),
    ],
)
def test_filename_from_disposition(header: str | None, expected: str | None) -> None:
    assert filename_from_disposition(header) == expected

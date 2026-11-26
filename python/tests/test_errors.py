from __future__ import annotations

import httpx
import pytest

from tembuilder import APIError, RenderFailedError, RenderStatus, RenderTimeoutError, TembuilderError
from tembuilder._errors import parse_retry_after


def test_reads_standard_error_body_and_retry_after() -> None:
    response = httpx.Response(
        503,
        json={"code": "COMMON_UNAVAILABLE", "description": "busy", "details": ["a", 3]},
        headers={"retry-after": "2"},
    )
    error = APIError.from_response(response)
    assert (error.status, error.code, error.description, error.details, error.retry_after_seconds) == (
        503,
        "COMMON_UNAVAILABLE",
        "busy",
        ["a", "3"],
        2,
    )
    assert str(error) == "COMMON_UNAVAILABLE (HTTP 503): busy"
    assert isinstance(error, TembuilderError)


def test_tolerates_missing_details() -> None:
    assert APIError.from_response(httpx.Response(400, json={"code": "X", "description": "y"})).details == []


def test_text_and_fallback_descriptions() -> None:
    assert APIError.from_response(httpx.Response(502, text="  bad gateway ")).description == "bad gateway"
    assert APIError.from_response(httpx.Response(500, content=b"")).description == "Internal Server Error"
    assert APIError.from_response(httpx.Response(599, content=b"")).description == "request failed"
    assert APIError.from_response(httpx.Response(500, json={"message": "x"})).code == "HTTP_500"
    assert APIError.from_response(httpx.Response(500, content=b"\xff\xfe")).code == "HTTP_500"


@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, None), ("7", 7), (" 3 ", 3), ("Wed, 21 Oct 2015 07:28:00 GMT", None), ("-1", None)],
)
def test_parse_retry_after(value: str | None, expected: int | None) -> None:
    assert parse_retry_after(value) == expected


def test_render_errors() -> None:
    failed = RenderStatus.from_dict(
        {"render_id": "5a6b7c8d-1e2f-4a3b-8c4d-5e6f7a8b9c0d", "status": "failed", "error_message": "bad"}
    )
    assert str(RenderFailedError(failed)).endswith("ended with status failed: bad")
    quota = RenderStatus.from_dict({"render_id": "5a6b7c8d-1e2f-4a3b-8c4d-5e6f7a8b9c0d", "status": "quota_exceeded"})
    assert str(RenderFailedError(quota)).endswith("ended with status quota_exceeded")
    timeout = RenderTimeoutError("r", None)
    assert timeout.last_status is None
    assert "unknown" in str(timeout)

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from ._generated.models.render_status import RenderStatus


class TembuilderError(Exception):
    """Base class of every error raised by the SDK."""


class APIError(TembuilderError):
    """The API answered with a non-2xx status. Branch on ``code`` (stable, e.g. ``TEMPLATE_NOT_FOUND``)."""

    def __init__(
        self,
        *,
        status: int,
        code: str,
        description: str,
        details: list[str] | None = None,
        retry_after_seconds: int | None = None,
    ) -> None:
        super().__init__(f"{code} (HTTP {status}): {description}")
        self.status = status
        self.code = code
        self.description = description
        self.details = details or []
        self.retry_after_seconds = retry_after_seconds

    @classmethod
    def from_response(cls, response: httpx.Response) -> APIError:
        """Builds an APIError from a read response. Non-standard bodies still yield an ``HTTP_<status>`` code."""
        retry_after = parse_retry_after(response.headers.get("retry-after"))
        body: Any
        try:
            body = response.json()
        except (json.JSONDecodeError, UnicodeDecodeError):
            body = None
        if isinstance(body, dict) and isinstance(body.get("code"), str) and isinstance(body.get("description"), str):
            details = body.get("details")
            return cls(
                status=response.status_code,
                code=body["code"],
                description=body["description"],
                details=[str(item) for item in details] if isinstance(details, list) else [],
                retry_after_seconds=retry_after,
            )
        text = response.text.strip() or response.reason_phrase or "request failed"
        return cls(
            status=response.status_code,
            code=f"HTTP_{response.status_code}",
            description=text,
            retry_after_seconds=retry_after,
        )


class ConnectionError(TembuilderError):
    """The request never produced a response (DNS, TLS, connection reset...)."""


class TimeoutError(TembuilderError):
    """An HTTP attempt exceeded the configured timeout."""


class RenderFailedError(TembuilderError):
    """A render reached the terminal ``failed`` or ``quota_exceeded`` status."""

    def __init__(self, render: RenderStatus) -> None:
        message = render.error_message if isinstance(render.error_message, str) else None
        super().__init__(
            f"render {render.render_id} ended with status {render.status}" + (f": {message}" if message else "")
        )
        self.render = render


class RenderTimeoutError(TembuilderError):
    """A render was still not terminal when the wait deadline passed."""

    def __init__(self, render_id: str, last_status: RenderStatus | None) -> None:
        state = last_status.status if last_status is not None else "unknown"
        super().__init__(f"render {render_id} did not finish before the deadline (last status: {state})")
        self.render_id = render_id
        self.last_status = last_status


class WebhookVerificationError(TembuilderError):
    """A webhook request failed signature, timestamp or payload verification."""


def parse_retry_after(value: str | None) -> int | None:
    """Parses a delta-seconds Retry-After value; HTTP-dates are ignored."""
    if value is None or not value.strip().isdigit():
        return None
    return int(value.strip())

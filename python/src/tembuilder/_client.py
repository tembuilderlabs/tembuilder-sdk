from __future__ import annotations

import datetime
import os
import re
import time
import urllib.parse
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from dataclasses import dataclass
from typing import Any, Literal, TypeVar
from uuid import UUID

import anyio
import httpx

from ._errors import APIError, ConnectionError, RenderFailedError, RenderTimeoutError, TembuilderError, TimeoutError
from ._generated.api.account import get_account
from ._generated.api.renders import create_render, download_render, get_render, list_renders
from ._generated.api.templates import get_template, list_templates
from ._generated.client import AuthenticatedClient as GeneratedClient
from ._generated.models.account import Account
from ._generated.models.render import Render
from ._generated.models.render_page import RenderPage
from ._generated.models.render_queued import RenderQueued
from ._generated.models.render_request import RenderRequest
from ._generated.models.render_request_parameters import RenderRequestParameters
from ._generated.models.render_status import RenderStatus
from ._generated.models.template import Template
from ._generated.models.template_detail import TemplateDetail
from ._generated.models.template_page import TemplatePage
from ._generated.types import UNSET, File, Response, Unset
from ._transport import AsyncRetryTransport, RetryPolicy, RetryTransport
from ._version import __version__

DEFAULT_BASE_URL = "https://api.tembuilder.com"
TERMINAL_FAILURES = frozenset({"failed", "quota_exceeded"})

T = TypeVar("T")
TemplateStatusFilter = Literal["all", "published", "draft"]
RenderStatusFilter = Literal["all", "pending", "success", "failed", "quota_exceeded"]


@dataclass(frozen=True)
class RenderFile:
    content: bytes
    content_type: str
    filename: str | None
    """Filename suggested by Content-Disposition, when present."""


@dataclass(frozen=True)
class _Config:
    api_key: str
    base_url: str
    timeout: float
    policy: RetryPolicy

    @classmethod
    def resolve(
        cls,
        api_key: str | None,
        base_url: str | None,
        timeout: float,
        max_retries: int,
        retry_base_delay: float,
        max_retry_delay: float,
    ) -> _Config:
        key = api_key or os.environ.get("TEMBUILDER_API_KEY")
        if not key:
            raise TembuilderError("An API key is required: pass api_key= or set TEMBUILDER_API_KEY.")
        url = (base_url or os.environ.get("TEMBUILDER_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        policy = RetryPolicy(max_retries=max_retries, base_delay=retry_base_delay, max_delay=max_retry_delay)
        return cls(api_key=key, base_url=url, timeout=timeout, policy=policy)

    @property
    def headers(self) -> dict[str, str]:
        return {"ApiKey": self.api_key, "User-Agent": f"tembuilder-python/{__version__}"}


def _raise_for_status(response: httpx.Response) -> None:
    if not response.is_success:
        response.read()
        raise APIError.from_response(response)


async def _araise_for_status(response: httpx.Response) -> None:
    if not response.is_success:
        await response.aread()
        raise APIError.from_response(response)


def _translate(error: httpx.HTTPError) -> TembuilderError:
    if isinstance(error, httpx.TimeoutException):
        return TimeoutError(f"request timed out: {error}")
    return ConnectionError(f"request failed: {error}")


def _parsed(response: Response[Any], expected: type[T]) -> T:
    # Error statuses never reach here: the response hook raises APIError first.
    if not isinstance(response.parsed, expected):
        raise TembuilderError(f"unexpected response body for HTTP {int(response.status_code)}")
    return response.parsed


def _opt(value: T | None) -> T | Unset:
    return UNSET if value is None else value


def _uuid(value: str | UUID | None) -> UUID | Unset:
    if value is None:
        return UNSET
    return value if isinstance(value, UUID) else UUID(value)


def _render_request(
    template_id: str | UUID, version: int | None, variant: str | None, parameters: dict[str, Any] | None
) -> RenderRequest:
    return RenderRequest(
        template_id=template_id if isinstance(template_id, UUID) else UUID(str(template_id)),
        version=_opt(version),
        variant=_opt(variant),
        parameters=UNSET if parameters is None else RenderRequestParameters.from_dict(parameters),
    )


def _render_file(response: Response[Any]) -> RenderFile:
    file = _parsed(response, File)
    return RenderFile(
        content=file.payload.read(),
        content_type=response.headers.get("content-type", "application/pdf"),
        filename=filename_from_disposition(response.headers.get("content-disposition")),
    )


def filename_from_disposition(header: str | None) -> str | None:
    """Extracts filename / filename* from a Content-Disposition header."""
    if not header:
        return None
    extended = re.search(r"filename\*\s*=\s*(?:UTF-8|utf-8)''([^;]+)", header)
    if extended:
        raw = extended.group(1).strip()
        try:
            return urllib.parse.unquote(raw, errors="strict")
        except UnicodeDecodeError:
            return raw
    plain = re.search(r'filename\s*=\s*"([^"]*)"|filename\s*=\s*([^;]+)', header)
    if not plain:
        return None
    return (plain.group(1) if plain.group(1) is not None else plain.group(2)).strip()


class _Waiter:
    """Polling state shared by the sync and async ``wait_for``."""

    def __init__(self, render_id: str, poll_interval: float, timeout: float, not_found_grace: float) -> None:
        self.render_id = render_id
        self.poll_interval = poll_interval
        started = time.monotonic()
        self.deadline = started + timeout
        self.not_found_until = started + not_found_grace
        self.last: RenderStatus | None = None

    def observe(self, status: RenderStatus) -> bool:
        """Records a status; True when it is a success, raises on a terminal failure."""
        self.last = status
        if status.status == "success":
            return True
        if status.status in TERMINAL_FAILURES:
            raise RenderFailedError(status)
        return False

    def tolerate(self, error: APIError) -> None:
        """Re-raises unless the error is the transitional 404 right after queueing."""
        if not (error.status == 404 and self.last is None and time.monotonic() < self.not_found_until):
            raise error

    def next_delay(self) -> float:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise RenderTimeoutError(self.render_id, self.last)
        return min(self.poll_interval, remaining)


class _SyncResources:
    def __init__(self, client: GeneratedClient) -> None:
        self._client = client

    def _call(self, operation: Callable[[], Response[Any]]) -> Response[Any]:
        try:
            return operation()
        except httpx.HTTPError as error:
            raise _translate(error) from error


class AccountResource(_SyncResources):
    def get(self) -> Account:
        """The project, workspace and scopes of the API key in use."""
        return _parsed(self._call(lambda: get_account.sync_detailed(client=self._client)), Account)


class TemplatesResource(_SyncResources):
    def list(
        self,
        *,
        status: TemplateStatusFilter | None = None,
        search: str | None = None,
        page: int | None = None,
        per_page: int | None = None,
    ) -> TemplatePage:
        """One page of templates, most recently updated first."""
        response = self._call(
            lambda: list_templates.sync_detailed(
                client=self._client,
                status=_opt(status),
                search=_opt(search),
                page=_opt(page),
                per_page=_opt(per_page),
            )
        )
        return _parsed(response, TemplatePage)

    def list_all(
        self, *, status: TemplateStatusFilter | None = None, search: str | None = None, per_page: int | None = None
    ) -> Iterator[Template]:
        """Iterates every template across pages."""
        page = 1
        while True:
            result = self.list(status=status, search=search, page=page, per_page=per_page)
            yield from result.data
            if not result.has_more:
                return
            page += 1

    def get(self, template_id: str, *, version: int | None = None) -> TemplateDetail:
        """A template (by UUID or slug) with its versions and render input contract."""
        response = self._call(
            lambda: get_template.sync_detailed(template_id, client=self._client, version=_opt(version))
        )
        return _parsed(response, TemplateDetail)


class RendersResource(_SyncResources):
    def create(
        self,
        template_id: str | UUID,
        *,
        version: int | None = None,
        variant: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> RenderQueued:
        """Queues a render. Returns the queued job, not the PDF."""
        body = _render_request(template_id, version, variant, parameters)
        return _parsed(self._call(lambda: create_render.sync_detailed(client=self._client, body=body)), RenderQueued)

    def get(self, render_id: str) -> RenderStatus:
        """Current status of a render."""
        return _parsed(self._call(lambda: get_render.sync_detailed(render_id, client=self._client)), RenderStatus)

    def list(
        self,
        *,
        status: RenderStatusFilter | None = None,
        template_id: str | UUID | None = None,
        started_after: datetime.datetime | None = None,
        started_before: datetime.datetime | None = None,
        page: int | None = None,
        per_page: int | None = None,
    ) -> RenderPage:
        """One page of the render log, newest first."""
        response = self._call(
            lambda: list_renders.sync_detailed(
                client=self._client,
                status=_opt(status),
                template_id=_uuid(template_id),
                started_after=_opt(started_after),
                started_before=_opt(started_before),
                page=_opt(page),
                per_page=_opt(per_page),
            )
        )
        return _parsed(response, RenderPage)

    def list_all(
        self,
        *,
        status: RenderStatusFilter | None = None,
        template_id: str | UUID | None = None,
        started_after: datetime.datetime | None = None,
        started_before: datetime.datetime | None = None,
        per_page: int | None = None,
    ) -> Iterator[Render]:
        """Iterates every render across pages."""
        page = 1
        while True:
            result = self.list(
                status=status,
                template_id=template_id,
                started_after=started_after,
                started_before=started_before,
                page=page,
                per_page=per_page,
            )
            yield from result.data
            if not result.has_more:
                return
            page += 1

    def download(self, render_id: str) -> RenderFile:
        """Downloads the PDF of a successful render."""
        return _render_file(self._call(lambda: download_render.sync_detailed(render_id, client=self._client)))

    def wait_for(
        self, render_id: str, *, poll_interval: float = 1.0, timeout: float = 120.0, not_found_grace: float = 15.0
    ) -> RenderStatus:
        """Polls until terminal. Returns on success; raises RenderFailedError or RenderTimeoutError."""
        waiter = _Waiter(render_id, poll_interval, timeout, not_found_grace)
        while True:
            try:
                status = self.get(render_id)
            except APIError as error:
                waiter.tolerate(error)
            else:
                if waiter.observe(status):
                    return status
            time.sleep(waiter.next_delay())

    def create_and_wait(
        self,
        template_id: str | UUID,
        *,
        version: int | None = None,
        variant: str | None = None,
        parameters: dict[str, Any] | None = None,
        poll_interval: float = 1.0,
        timeout: float = 120.0,
        not_found_grace: float = 15.0,
    ) -> RenderStatus:
        """Queues a render and waits for it to finish (see wait_for)."""
        queued = self.create(template_id, version=version, variant=variant, parameters=parameters)
        return self.wait_for(
            str(queued.render_id), poll_interval=poll_interval, timeout=timeout, not_found_grace=not_found_grace
        )


class Tembuilder:
    """Synchronous Tembuilder API client.

    >>> client = Tembuilder(api_key="...")
    >>> status = client.renders.create_and_wait(template_id, parameters={"customer": "Acme"})
    >>> pdf = client.renders.download(str(status.render_id))
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 2,
        retry_base_delay: float = 0.5,
        max_retry_delay: float = 8.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        config = _Config.resolve(api_key, base_url, timeout, max_retries, retry_base_delay, max_retry_delay)
        self._http = httpx.Client(
            base_url=config.base_url,
            headers=config.headers,
            timeout=config.timeout,
            transport=RetryTransport(transport or httpx.HTTPTransport(), config.policy),
            event_hooks={"response": [_raise_for_status]},
        )
        generated = GeneratedClient(base_url=config.base_url, token=config.api_key).set_httpx_client(self._http)
        self.account = AccountResource(generated)
        self.templates = TemplatesResource(generated)
        self.renders = RendersResource(generated)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> Tembuilder:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


class _AsyncResources:
    def __init__(self, client: GeneratedClient) -> None:
        self._client = client

    async def _call(self, operation: Callable[[], Awaitable[Response[Any]]]) -> Response[Any]:
        try:
            return await operation()
        except httpx.HTTPError as error:
            raise _translate(error) from error


class AsyncAccountResource(_AsyncResources):
    async def get(self) -> Account:
        return _parsed(await self._call(lambda: get_account.asyncio_detailed(client=self._client)), Account)


class AsyncTemplatesResource(_AsyncResources):
    async def list(
        self,
        *,
        status: TemplateStatusFilter | None = None,
        search: str | None = None,
        page: int | None = None,
        per_page: int | None = None,
    ) -> TemplatePage:
        response = await self._call(
            lambda: list_templates.asyncio_detailed(
                client=self._client,
                status=_opt(status),
                search=_opt(search),
                page=_opt(page),
                per_page=_opt(per_page),
            )
        )
        return _parsed(response, TemplatePage)

    async def list_all(
        self, *, status: TemplateStatusFilter | None = None, search: str | None = None, per_page: int | None = None
    ) -> AsyncIterator[Template]:
        page = 1
        while True:
            result = await self.list(status=status, search=search, page=page, per_page=per_page)
            for item in result.data:
                yield item
            if not result.has_more:
                return
            page += 1

    async def get(self, template_id: str, *, version: int | None = None) -> TemplateDetail:
        response = await self._call(
            lambda: get_template.asyncio_detailed(template_id, client=self._client, version=_opt(version))
        )
        return _parsed(response, TemplateDetail)


class AsyncRendersResource(_AsyncResources):
    async def create(
        self,
        template_id: str | UUID,
        *,
        version: int | None = None,
        variant: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> RenderQueued:
        body = _render_request(template_id, version, variant, parameters)
        response = await self._call(lambda: create_render.asyncio_detailed(client=self._client, body=body))
        return _parsed(response, RenderQueued)

    async def get(self, render_id: str) -> RenderStatus:
        response = await self._call(lambda: get_render.asyncio_detailed(render_id, client=self._client))
        return _parsed(response, RenderStatus)

    async def list(
        self,
        *,
        status: RenderStatusFilter | None = None,
        template_id: str | UUID | None = None,
        started_after: datetime.datetime | None = None,
        started_before: datetime.datetime | None = None,
        page: int | None = None,
        per_page: int | None = None,
    ) -> RenderPage:
        response = await self._call(
            lambda: list_renders.asyncio_detailed(
                client=self._client,
                status=_opt(status),
                template_id=_uuid(template_id),
                started_after=_opt(started_after),
                started_before=_opt(started_before),
                page=_opt(page),
                per_page=_opt(per_page),
            )
        )
        return _parsed(response, RenderPage)

    async def list_all(
        self,
        *,
        status: RenderStatusFilter | None = None,
        template_id: str | UUID | None = None,
        started_after: datetime.datetime | None = None,
        started_before: datetime.datetime | None = None,
        per_page: int | None = None,
    ) -> AsyncIterator[Render]:
        page = 1
        while True:
            result = await self.list(
                status=status,
                template_id=template_id,
                started_after=started_after,
                started_before=started_before,
                page=page,
                per_page=per_page,
            )
            for item in result.data:
                yield item
            if not result.has_more:
                return
            page += 1

    async def download(self, render_id: str) -> RenderFile:
        return _render_file(await self._call(lambda: download_render.asyncio_detailed(render_id, client=self._client)))

    async def wait_for(
        self, render_id: str, *, poll_interval: float = 1.0, timeout: float = 120.0, not_found_grace: float = 15.0
    ) -> RenderStatus:
        waiter = _Waiter(render_id, poll_interval, timeout, not_found_grace)
        while True:
            try:
                status = await self.get(render_id)
            except APIError as error:
                waiter.tolerate(error)
            else:
                if waiter.observe(status):
                    return status
            await anyio.sleep(waiter.next_delay())

    async def create_and_wait(
        self,
        template_id: str | UUID,
        *,
        version: int | None = None,
        variant: str | None = None,
        parameters: dict[str, Any] | None = None,
        poll_interval: float = 1.0,
        timeout: float = 120.0,
        not_found_grace: float = 15.0,
    ) -> RenderStatus:
        queued = await self.create(template_id, version=version, variant=variant, parameters=parameters)
        return await self.wait_for(
            str(queued.render_id), poll_interval=poll_interval, timeout=timeout, not_found_grace=not_found_grace
        )


class AsyncTembuilder:
    """Asynchronous Tembuilder API client (asyncio or trio via anyio)."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 2,
        retry_base_delay: float = 0.5,
        max_retry_delay: float = 8.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        config = _Config.resolve(api_key, base_url, timeout, max_retries, retry_base_delay, max_retry_delay)
        self._http = httpx.AsyncClient(
            base_url=config.base_url,
            headers=config.headers,
            timeout=config.timeout,
            transport=AsyncRetryTransport(transport or httpx.AsyncHTTPTransport(), config.policy),
            event_hooks={"response": [_araise_for_status]},
        )
        generated = GeneratedClient(base_url=config.base_url, token=config.api_key).set_async_httpx_client(self._http)
        self.account = AsyncAccountResource(generated)
        self.templates = AsyncTemplatesResource(generated)
        self.renders = AsyncRendersResource(generated)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> AsyncTembuilder:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

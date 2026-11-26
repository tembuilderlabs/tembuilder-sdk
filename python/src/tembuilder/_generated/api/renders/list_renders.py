import datetime
from http import HTTPStatus
from typing import Any
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...models.list_renders_status import ListRendersStatus
from ...models.render_page import RenderPage
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    page: int | Unset = UNSET,
    per_page: int | Unset = UNSET,
    status: ListRendersStatus | Unset = UNSET,
    template_id: UUID | Unset = UNSET,
    started_after: datetime.datetime | Unset = UNSET,
    started_before: datetime.datetime | Unset = UNSET,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["page"] = page

    params["per_page"] = per_page

    json_status: str | Unset = UNSET
    if not isinstance(status, Unset):
        json_status = status

    params["status"] = json_status

    json_template_id: str | Unset = UNSET
    if not isinstance(template_id, Unset):
        json_template_id = str(template_id)
    params["template_id"] = json_template_id

    json_started_after: str | Unset = UNSET
    if not isinstance(started_after, Unset):
        json_started_after = started_after.isoformat()
    params["started_after"] = json_started_after

    json_started_before: str | Unset = UNSET
    if not isinstance(started_before, Unset):
        json_started_before = started_before.isoformat()
    params["started_before"] = json_started_before

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/renders",
        "params": params,
    }

    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | RenderPage | None:
    if response.status_code == 200:
        response_200 = RenderPage.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = Error.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = Error.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = Error.from_dict(response.json())

        return response_403

    if response.status_code == 500:
        response_500 = Error.from_dict(response.json())

        return response_500

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Error | RenderPage]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    page: int | Unset = UNSET,
    per_page: int | Unset = UNSET,
    status: ListRendersStatus | Unset = UNSET,
    template_id: UUID | Unset = UNSET,
    started_after: datetime.datetime | Unset = UNSET,
    started_before: datetime.datetime | Unset = UNSET,
) -> Response[Error | RenderPage]:
    """List renders

     Lists the project's renders, newest first. Render parameters are not
    returned. Requires the `template:read` or `template:render` scope.

    Args:
        page (int | Unset):
        per_page (int | Unset):
        status (ListRendersStatus | Unset):
        template_id (UUID | Unset):
        started_after (datetime.datetime | Unset):
        started_before (datetime.datetime | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | RenderPage]
    """

    kwargs = _get_kwargs(
        page=page,
        per_page=per_page,
        status=status,
        template_id=template_id,
        started_after=started_after,
        started_before=started_before,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    page: int | Unset = UNSET,
    per_page: int | Unset = UNSET,
    status: ListRendersStatus | Unset = UNSET,
    template_id: UUID | Unset = UNSET,
    started_after: datetime.datetime | Unset = UNSET,
    started_before: datetime.datetime | Unset = UNSET,
) -> Error | RenderPage | None:
    """List renders

     Lists the project's renders, newest first. Render parameters are not
    returned. Requires the `template:read` or `template:render` scope.

    Args:
        page (int | Unset):
        per_page (int | Unset):
        status (ListRendersStatus | Unset):
        template_id (UUID | Unset):
        started_after (datetime.datetime | Unset):
        started_before (datetime.datetime | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | RenderPage
    """

    return sync_detailed(
        client=client,
        page=page,
        per_page=per_page,
        status=status,
        template_id=template_id,
        started_after=started_after,
        started_before=started_before,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    page: int | Unset = UNSET,
    per_page: int | Unset = UNSET,
    status: ListRendersStatus | Unset = UNSET,
    template_id: UUID | Unset = UNSET,
    started_after: datetime.datetime | Unset = UNSET,
    started_before: datetime.datetime | Unset = UNSET,
) -> Response[Error | RenderPage]:
    """List renders

     Lists the project's renders, newest first. Render parameters are not
    returned. Requires the `template:read` or `template:render` scope.

    Args:
        page (int | Unset):
        per_page (int | Unset):
        status (ListRendersStatus | Unset):
        template_id (UUID | Unset):
        started_after (datetime.datetime | Unset):
        started_before (datetime.datetime | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | RenderPage]
    """

    kwargs = _get_kwargs(
        page=page,
        per_page=per_page,
        status=status,
        template_id=template_id,
        started_after=started_after,
        started_before=started_before,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    page: int | Unset = UNSET,
    per_page: int | Unset = UNSET,
    status: ListRendersStatus | Unset = UNSET,
    template_id: UUID | Unset = UNSET,
    started_after: datetime.datetime | Unset = UNSET,
    started_before: datetime.datetime | Unset = UNSET,
) -> Error | RenderPage | None:
    """List renders

     Lists the project's renders, newest first. Render parameters are not
    returned. Requires the `template:read` or `template:render` scope.

    Args:
        page (int | Unset):
        per_page (int | Unset):
        status (ListRendersStatus | Unset):
        template_id (UUID | Unset):
        started_after (datetime.datetime | Unset):
        started_before (datetime.datetime | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | RenderPage
    """

    return (
        await asyncio_detailed(
            client=client,
            page=page,
            per_page=per_page,
            status=status,
            template_id=template_id,
            started_after=started_after,
            started_before=started_before,
        )
    ).parsed

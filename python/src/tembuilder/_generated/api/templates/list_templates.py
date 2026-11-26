from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...models.list_templates_status import ListTemplatesStatus
from ...models.template_page import TemplatePage
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    page: int | Unset = UNSET,
    per_page: int | Unset = UNSET,
    status: ListTemplatesStatus | Unset = UNSET,
    search: str | Unset = UNSET,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["page"] = page

    params["per_page"] = per_page

    json_status: str | Unset = UNSET
    if not isinstance(status, Unset):
        json_status = status

    params["status"] = json_status

    params["search"] = search

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/templates",
        "params": params,
    }

    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | TemplatePage | None:
    if response.status_code == 200:
        response_200 = TemplatePage.from_dict(response.json())

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


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Error | TemplatePage]:
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
    status: ListTemplatesStatus | Unset = UNSET,
    search: str | Unset = UNSET,
) -> Response[Error | TemplatePage]:
    """List templates

     Lists the project's templates, most recently updated first. `status`
    filters by the status of each template's current version; use
    `published_versions` to see every version you can render.
    Requires the `template:read` or `template:render` scope.

    Args:
        page (int | Unset):
        per_page (int | Unset):
        status (ListTemplatesStatus | Unset):
        search (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | TemplatePage]
    """

    kwargs = _get_kwargs(
        page=page,
        per_page=per_page,
        status=status,
        search=search,
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
    status: ListTemplatesStatus | Unset = UNSET,
    search: str | Unset = UNSET,
) -> Error | TemplatePage | None:
    """List templates

     Lists the project's templates, most recently updated first. `status`
    filters by the status of each template's current version; use
    `published_versions` to see every version you can render.
    Requires the `template:read` or `template:render` scope.

    Args:
        page (int | Unset):
        per_page (int | Unset):
        status (ListTemplatesStatus | Unset):
        search (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | TemplatePage
    """

    return sync_detailed(
        client=client,
        page=page,
        per_page=per_page,
        status=status,
        search=search,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    page: int | Unset = UNSET,
    per_page: int | Unset = UNSET,
    status: ListTemplatesStatus | Unset = UNSET,
    search: str | Unset = UNSET,
) -> Response[Error | TemplatePage]:
    """List templates

     Lists the project's templates, most recently updated first. `status`
    filters by the status of each template's current version; use
    `published_versions` to see every version you can render.
    Requires the `template:read` or `template:render` scope.

    Args:
        page (int | Unset):
        per_page (int | Unset):
        status (ListTemplatesStatus | Unset):
        search (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | TemplatePage]
    """

    kwargs = _get_kwargs(
        page=page,
        per_page=per_page,
        status=status,
        search=search,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    page: int | Unset = UNSET,
    per_page: int | Unset = UNSET,
    status: ListTemplatesStatus | Unset = UNSET,
    search: str | Unset = UNSET,
) -> Error | TemplatePage | None:
    """List templates

     Lists the project's templates, most recently updated first. `status`
    filters by the status of each template's current version; use
    `published_versions` to see every version you can render.
    Requires the `template:read` or `template:render` scope.

    Args:
        page (int | Unset):
        per_page (int | Unset):
        status (ListTemplatesStatus | Unset):
        search (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | TemplatePage
    """

    return (
        await asyncio_detailed(
            client=client,
            page=page,
            per_page=per_page,
            status=status,
            search=search,
        )
    ).parsed

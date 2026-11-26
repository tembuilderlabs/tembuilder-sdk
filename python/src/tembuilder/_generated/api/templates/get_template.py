from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...models.template_detail import TemplateDetail
from ...types import UNSET, Response, Unset


def _get_kwargs(
    template_id: str,
    *,
    version: int | Unset = UNSET,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["version"] = version

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/templates/{template_id}".format(
            template_id=quote(str(template_id), safe=""),
        ),
        "params": params,
    }

    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | TemplateDetail | None:
    if response.status_code == 200:
        response_200 = TemplateDetail.from_dict(response.json())

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

    if response.status_code == 404:
        response_404 = Error.from_dict(response.json())

        return response_404

    if response.status_code == 500:
        response_500 = Error.from_dict(response.json())

        return response_500

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Error | TemplateDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    template_id: str,
    *,
    client: AuthenticatedClient | Client,
    version: int | Unset = UNSET,
) -> Response[Error | TemplateDetail]:
    """Get a template and its render input

     Returns the template, its versions and the input contract of one
    version: variants, parameter definitions, a JSON Schema for the
    `parameters` object and an example value. Accepts the template UUID or
    its slug. Requires the `template:read` or `template:render` scope.

    Args:
        template_id (str):
        version (int | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | TemplateDetail]
    """

    kwargs = _get_kwargs(
        template_id=template_id,
        version=version,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    template_id: str,
    *,
    client: AuthenticatedClient | Client,
    version: int | Unset = UNSET,
) -> Error | TemplateDetail | None:
    """Get a template and its render input

     Returns the template, its versions and the input contract of one
    version: variants, parameter definitions, a JSON Schema for the
    `parameters` object and an example value. Accepts the template UUID or
    its slug. Requires the `template:read` or `template:render` scope.

    Args:
        template_id (str):
        version (int | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | TemplateDetail
    """

    return sync_detailed(
        template_id=template_id,
        client=client,
        version=version,
    ).parsed


async def asyncio_detailed(
    template_id: str,
    *,
    client: AuthenticatedClient | Client,
    version: int | Unset = UNSET,
) -> Response[Error | TemplateDetail]:
    """Get a template and its render input

     Returns the template, its versions and the input contract of one
    version: variants, parameter definitions, a JSON Schema for the
    `parameters` object and an example value. Accepts the template UUID or
    its slug. Requires the `template:read` or `template:render` scope.

    Args:
        template_id (str):
        version (int | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | TemplateDetail]
    """

    kwargs = _get_kwargs(
        template_id=template_id,
        version=version,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    template_id: str,
    *,
    client: AuthenticatedClient | Client,
    version: int | Unset = UNSET,
) -> Error | TemplateDetail | None:
    """Get a template and its render input

     Returns the template, its versions and the input contract of one
    version: variants, parameter definitions, a JSON Schema for the
    `parameters` object and an example value. Accepts the template UUID or
    its slug. Requires the `template:read` or `template:render` scope.

    Args:
        template_id (str):
        version (int | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | TemplateDetail
    """

    return (
        await asyncio_detailed(
            template_id=template_id,
            client=client,
            version=version,
        )
    ).parsed

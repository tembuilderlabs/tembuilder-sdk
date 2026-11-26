from http import HTTPStatus
from io import BytesIO
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...types import File, Response


def _get_kwargs(
    render_id: str,
) -> dict[str, Any]:
    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/renders/{render_id}/download".format(
            render_id=quote(str(render_id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | File | None:
    if response.status_code == 200:
        response_200 = File(payload=BytesIO(response.content))

        return response_200

    if response.status_code == 401:
        response_401 = Error.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = Error.from_dict(response.json())

        return response_403

    if response.status_code == 404:
        response_404 = Error.from_dict(response.json())

        return response_404

    if response.status_code == 502:
        response_502 = Error.from_dict(response.json())

        return response_502

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Error | File]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    render_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[Error | File]:
    """Download a render's PDF

     Streams the PDF of a successful render while it is retained. This is
    an authenticated endpoint, not a permanent public URL.
    Requires the `template:render` scope.

    Args:
        render_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | File]
    """

    kwargs = _get_kwargs(
        render_id=render_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    render_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Error | File | None:
    """Download a render's PDF

     Streams the PDF of a successful render while it is retained. This is
    an authenticated endpoint, not a permanent public URL.
    Requires the `template:render` scope.

    Args:
        render_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | File
    """

    return sync_detailed(
        render_id=render_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    render_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[Error | File]:
    """Download a render's PDF

     Streams the PDF of a successful render while it is retained. This is
    an authenticated endpoint, not a permanent public URL.
    Requires the `template:render` scope.

    Args:
        render_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | File]
    """

    kwargs = _get_kwargs(
        render_id=render_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    render_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Error | File | None:
    """Download a render's PDF

     Streams the PDF of a successful render while it is retained. This is
    an authenticated endpoint, not a permanent public URL.
    Requires the `template:render` scope.

    Args:
        render_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | File
    """

    return (
        await asyncio_detailed(
            render_id=render_id,
            client=client,
        )
    ).parsed

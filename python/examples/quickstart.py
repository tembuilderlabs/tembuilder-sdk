"""Mirrors the README quickstart; type-checked in CI so the docs stay correct."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from pathlib import Path

from tembuilder import AsyncTembuilder, Tembuilder, verify_webhook


def quickstart() -> None:
    with Tembuilder() as client:
        template = client.templates.get("invoice")
        example = template.input_.example_parameters.to_dict()

        status = client.renders.create_and_wait(template.id, parameters={**example, "customer": "Acme Corp"})
        pdf = client.renders.download(str(status.render_id))
        Path(pdf.filename or "output.pdf").write_bytes(pdf.content)


async def list_published() -> None:
    async with AsyncTembuilder() as client:
        async for template in client.templates.list_all(status="published"):
            print(template.slug, template.published_versions)


def handle_webhook(body: bytes, headers: Mapping[str, str], secret: str) -> None:
    event = verify_webhook(payload=body, headers=headers, secret=secret)
    if event["type"] == "renders.status":
        print(event["data"]["render_id"], event["data"]["status"])


if __name__ == "__main__":
    quickstart()
    asyncio.run(list_published())

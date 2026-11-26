"""A fresh consumer app for the Python SDK.

e2e/run.sh installs ``tembuilder`` into an empty virtualenv (from the built
wheel or from PyPI) and runs this file, so it proves the package as users get
it: imports, version, webhooks and, with TEMBUILDER_API_KEY, TEMBUILDER_BASE_URL
and TEMBUILDER_SMOKE_TEMPLATE, a real render through the sync and async clients.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from collections.abc import Callable
from pathlib import Path

from tembuilder import APIError, AsyncTembuilder, Tembuilder, __version__, verify_webhook

LIVE = ("TEMBUILDER_API_KEY", "TEMBUILDER_BASE_URL", "TEMBUILDER_SMOKE_TEMPLATE")


def step(name: str) -> None:
    print(f"- {name}", flush=True)


def expect_api_error(call: Callable[[], object], status: int) -> APIError:
    try:
        call()
    except APIError as error:
        assert error.status == status, f"expected HTTP {status}, got {error.status}"
        return error
    raise AssertionError(f"expected HTTP {status}, call succeeded")


def offline() -> None:
    step(f"installed version {__version__}")
    expected = os.environ.get("EXPECTED_VERSION")
    if expected:
        assert __version__ == expected, f"{__version__} != {expected}"

    step("webhook signature vectors")
    contract = json.loads(Path(os.environ["WEBHOOK_VECTORS"]).read_text())
    for vector in contract["vectors"]:
        headers = {"tembuilder-timestamp": vector["timestamp"], "tembuilder-signature": vector["signature"]}
        try:
            verify_webhook(payload=vector["body"], headers=headers, secret=contract["secret"], now=vector["now"])
            valid = True
        except Exception:
            valid = False
        assert valid == vector["valid"], vector["name"]


def live_sync(template_ref: str) -> None:
    with Tembuilder() as client:
        step("account")
        assert client.account.get().project.id

        step("template detail and input contract")
        template = client.templates.get(template_ref)
        assert template.published_versions, "smoke template has no published version"
        version = template.published_versions[-1]
        detail = client.templates.get(str(template.id), version=version)
        assert detail.input_.version == version

        step("template list contains it")
        assert any(item.id == template.id for item in client.templates.list_all(search=template.slug))

        step("render, wait and download")
        status = client.renders.create_and_wait(
            template.id,
            version=version,
            parameters=detail.input_.example_parameters.to_dict(),
            poll_interval=2.0,
            timeout=180.0,
        )
        pdf = client.renders.download(str(status.render_id))
        assert pdf.content[:5] == b"%PDF-"

        step("render log contains it")
        page = client.renders.list(template_id=template.id, per_page=20)
        assert any(render.id == status.render_id for render in page.data)

        step("typed errors: unknown template is 404, bad key is 401")
        expect_api_error(lambda: client.templates.get("e2e-template-that-does-not-exist"), 404)
    with Tembuilder(api_key="invalid") as bad:
        assert expect_api_error(bad.account.get, 401).code == "COMMON_UNAUTHENTICATED"


async def live_async(template_ref: str) -> None:
    step("async client: account and template")
    async with AsyncTembuilder() as client:
        account = await client.account.get()
        template = await client.templates.get(template_ref)
        assert account.project.id and template.id


def main() -> None:
    offline()
    if not all(os.environ.get(name) for name in LIVE):
        assert os.environ.get("REQUIRE_LIVE") != "1", "REQUIRE_LIVE=1 but the live environment is not set"
        print("live API: skipped (TEMBUILDER_API_KEY, TEMBUILDER_BASE_URL, TEMBUILDER_SMOKE_TEMPLATE not set)")
        print("python e2e ok")
        sys.exit(0)
    template_ref = os.environ["TEMBUILDER_SMOKE_TEMPLATE"]
    live_sync(template_ref)
    asyncio.run(live_async(template_ref))
    print("python e2e ok (live)")


if __name__ == "__main__":
    main()

# tembuilder

Official Python SDK for the [Tembuilder](https://tembuilder.com) PDF rendering API.

```bash
pip install tembuilder
```

Requires Python 3.11+. Sync and async (asyncio or trio) clients, fully typed.

## Quickstart

```python
from pathlib import Path

from tembuilder import Tembuilder

with Tembuilder(api_key="...") as client:  # or TEMBUILDER_API_KEY
    template = client.templates.get("invoice")
    example = template.input_.example_parameters.to_dict()

    status = client.renders.create_and_wait(
        template.id, parameters={**example, "customer": "Acme Corp"}
    )
    pdf = client.renders.download(str(status.render_id))
    Path(pdf.filename or "output.pdf").write_bytes(pdf.content)
```

Async:

```python
from tembuilder import AsyncTembuilder

async with AsyncTembuilder() as client:
    async for template in client.templates.list_all(status="published"):
        print(template.slug, template.published_versions)
```

## API

| Call | HTTP |
| --- | --- |
| `account.get()` | `GET /v1/me` |
| `templates.list(...)` / `templates.list_all(...)` | `GET /v1/templates` |
| `templates.get(id_or_slug, version=)` | `GET /v1/templates/{id}` |
| `renders.create(template_id, version=, variant=, parameters=)` | `POST /v1/pdf/render` |
| `renders.get(render_id)` | `GET /v1/renders/{id}` |
| `renders.list(...)` / `renders.list_all(...)` | `GET /v1/renders` |
| `renders.download(render_id)` | `GET /v1/renders/{id}/download` |
| `renders.wait_for(...)` / `renders.create_and_wait(...)` | polling |

Models (`Template`, `TemplateDetail`, `RenderStatus`, …) are generated from
the OpenAPI contract; call `.to_dict()` for plain data.

## Configuration

`Tembuilder(api_key=None, base_url=None, timeout=30.0, max_retries=2,
retry_base_delay=0.5, max_retry_delay=8.0, transport=None)`. `api_key` and
`base_url` default to `TEMBUILDER_API_KEY` / `TEMBUILDER_BASE_URL`.

Retries follow the same rules as every Tembuilder SDK: GETs are retried on
transport errors and 429/502/503/504; `renders.create` only on 429/503 and
never after a transport error.

## Errors

`TembuilderError` ← `APIError` (`status`, `code`, `description`, `details`,
`retry_after_seconds`), `ConnectionError`, `TimeoutError`,
`RenderFailedError` (`render`), `RenderTimeoutError` (`render_id`,
`last_status`), `WebhookVerificationError`.

## Webhooks

```python
from tembuilder import verify_webhook

event = verify_webhook(payload=request.body, headers=request.headers, secret=SECRET)
if event["type"] == "renders.status":
    ...
```

Pass the raw body bytes. Timestamps outside ±300 s are rejected.

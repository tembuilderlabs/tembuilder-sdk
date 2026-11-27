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

## Rendering: pick the flow that fits

A render is a background job. `renders.create` returns a `render_id` within
milliseconds; the PDF is produced afterwards. No call keeps a connection open
while the PDF renders, so choose by where your code runs:

| Flow | Use it for |
| --- | --- |
| 1. Create, then wait | Scripts, CLIs, cron jobs |
| 2. Create now, check later | Web requests and task queues: store the id, return at once |
| 3. Create, get a webhook | Servers: Tembuilder calls you when the render ends |

### 1. Create, then wait

`create_and_wait` = `create` + `wait_for`. It polls the status every second
(`poll_interval`) for up to two minutes (`timeout`).

```python
status = client.renders.create_and_wait(
    template.id, parameters={"customer": "Acme Corp"}, poll_interval=2.0, timeout=60.0
)
pdf = client.renders.download(str(status.render_id))
```

Already have a `render_id`? `client.renders.wait_for(render_id)`.

### 2. Create now, check later

```python
# In the request handler: queue the render and answer immediately.
queued = client.renders.create(template.id, parameters={"customer": "Acme Corp"})
order.render_id = str(queued.render_id)  # keep the id
order.save()

# Later (another request, a Celery task, a "check status" button):
status = client.renders.get(order.render_id)
if status.status == "pending":
    pass  # not ready yet: check again later
elif status.status == "success":
    pdf = client.renders.download(order.render_id)
    Path(pdf.filename or "output.pdf").write_bytes(pdf.content)
else:  # "failed" or "quota_exceeded"
    print(status.status, status.error_message)
```

Right after `create`, `renders.get` can raise `APIError` with `status == 404`
for a moment while the job is being registered; treat it like `pending`.
`renders.list(status="pending")` returns every render still running. With
`AsyncTembuilder`, the same calls are awaited.

### 3. Create, get a webhook

Add a webhook endpoint in the Tembuilder app (**Webhooks** in the project sidebar), then
create renders as in flow 2 and download when the `renders.status` event
arrives (see [Webhooks](#webhooks)):

```python
if event["type"] == "renders.status" and event["data"]["status"] == "success":
    pdf = client.renders.download(event["data"]["render_id"])
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

## Versioning

The SDK follows [Semantic Versioning](https://semver.org). Before 1.0, a minor
release may contain breaking changes; patch releases never do. Each release
is tagged in this repository and listed in the changelog.

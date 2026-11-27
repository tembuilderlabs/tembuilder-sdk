# @tembuilderlabs/sdk

Official Node.js / TypeScript SDK for the [Tembuilder](https://tembuilder.com) PDF rendering API.

```bash
npm install @tembuilderlabs/sdk
```

Requires Node 20+. Fully typed from the public OpenAPI contract.

## Quickstart

```ts
import { writeFile } from 'node:fs/promises'
import { Tembuilder } from '@tembuilderlabs/sdk'

const tembuilder = new Tembuilder({ apiKey: process.env.TEMBUILDER_API_KEY })

// Discover what a template accepts.
const template = await tembuilder.templates.get('invoice')
console.log(template.input.parameters_schema, template.input.example_parameters)

// Render and wait for the result.
const render = await tembuilder.renders.createAndWait({
  template_id: template.id,
  parameters: { ...template.input.example_parameters, customer: 'Acme Corp' },
})
const pdf = await tembuilder.renders.download(render.render_id)
await writeFile(pdf.filename ?? 'output.pdf', pdf.bytes)
```

## Rendering: pick the flow that fits

A render is a background job. `renders.create` returns a `render_id` within
milliseconds; the PDF is produced afterwards. No call keeps a connection open
while the PDF renders, so choose by where your code runs:

| Flow | Use it for |
| --- | --- |
| 1. Create, then wait | Scripts, CLIs, cron jobs |
| 2. Create now, check later | Web requests and queues: store the id, return at once |
| 3. Create, get a webhook | Servers: Tembuilder calls you when the render ends |

### 1. Create, then wait

`createAndWait` = `create` + `waitFor`. It polls the status every second
(`pollIntervalMs`) for up to two minutes (`timeoutMs`).

```ts
const status = await tembuilder.renders.createAndWait(
  { template_id: template.id, parameters: { customer: 'Acme Corp' } },
  { pollIntervalMs: 2_000, timeoutMs: 60_000 },
)
const pdf = await tembuilder.renders.download(status.render_id)
```

Already have a `render_id`? `await tembuilder.renders.waitFor(renderId)`.

### 2. Create now, check later

```ts
// In the request handler: queue the render and answer immediately.
const { render_id } = await tembuilder.renders.create({
  template_id: template.id,
  parameters: { customer: 'Acme Corp' },
})
await db.orders.update(orderId, { renderId: render_id }) // keep the id

// Later (another request, a job, a "check status" button):
const status = await tembuilder.renders.get(render_id)
switch (status.status) {
  case 'pending':
    break // not ready yet: check again later
  case 'success': {
    const pdf = await tembuilder.renders.download(render_id)
    await writeFile(pdf.filename ?? 'output.pdf', pdf.bytes)
    break
  }
  default: // 'failed' or 'quota_exceeded'
    console.error(status.status, status.error_message)
}
```

Right after `create`, `renders.get` can answer `404` for a moment while the
job is being registered; treat it like `pending`. `renders.list({ status:
'pending' })` returns every render still running.

### 3. Create, get a webhook

Add a webhook endpoint in the Tembuilder app (**Webhooks** in the project sidebar), then
create renders as in flow 2 and download when the `renders.status` event
arrives (see [Webhooks](#webhooks)):

```ts
if (event.type === 'renders.status' && event.data.status === 'success') {
  const pdf = await tembuilder.renders.download(event.data.render_id)
}
```

## API

| Call | HTTP |
| --- | --- |
| `account.get()` | `GET /v1/me` |
| `templates.list(params)` / `templates.listAll(params)` | `GET /v1/templates` |
| `templates.get(idOrSlug, { version })` | `GET /v1/templates/{id}` |
| `renders.create(request)` | `POST /v1/pdf/render` |
| `renders.get(renderId)` | `GET /v1/renders/{id}` |
| `renders.list(params)` / `renders.listAll(params)` | `GET /v1/renders` |
| `renders.download(renderId)` | `GET /v1/renders/{id}/download` |
| `renders.waitFor(renderId, options)` / `renders.createAndWait(request, options)` | polling |

## Configuration

| Option | Default |
| --- | --- |
| `apiKey` | `TEMBUILDER_API_KEY` |
| `baseUrl` | `TEMBUILDER_BASE_URL`, then `https://api.tembuilder.com` |
| `timeoutMs` (per attempt) | 30 000 |
| `maxRetries` | 2 |
| `retryBaseDelayMs` / `maxRetryDelayMs` | 500 / 8 000 |
| `fetch` | `globalThis.fetch` |

Retries: GETs are retried on network errors, timeouts and 429/502/503/504.
`renders.create` is retried only on 429/503, which mean the render was not
accepted; it is never resent after a network error, because it may have been.
A `Retry-After` header is honoured (capped by `maxRetryDelayMs`).

## Errors

All errors extend `TembuilderError`:

- `APIError` — non-2xx response: `status`, `code` (stable, e.g. `TEMPLATE_NOT_FOUND`), `description`, `details`, `retryAfterSeconds`.
- `ConnectionError`, `TimeoutError` — no response.
- `RenderFailedError` (`render`) — the render ended `failed` / `quota_exceeded`.
- `RenderTimeoutError` (`renderId`, `lastStatus`) — `waitFor` deadline passed.
- `WebhookVerificationError` — see below.

## Webhooks

```ts
import { verifyWebhook } from '@tembuilderlabs/sdk'

app.post('/webhooks/tembuilder', express.raw({ type: 'application/json' }), (req, res) => {
  const event = verifyWebhook({ payload: req.body, headers: req.headers, secret: process.env.TEMBUILDER_WEBHOOK_SECRET! })
  if (event.type === 'renders.status') {
    // event.data.render_id, event.data.status, event.data.output?.download_url
  }
  res.sendStatus(204)
})
```

Pass the raw body, never a re-serialized object. Timestamps older than
5 minutes are rejected (`toleranceSeconds`). Deduplicate by
`Tembuilder-Delivery-Id`: deliveries are at-least-once.

# tembuilder-go

Official Go SDK for the [Tembuilder](https://tembuilder.com) PDF rendering API.

```bash
go get github.com/tembuilderlabs/tembuilder-sdk/go
```

Requires Go 1.24+.

## Quickstart

```go
import tembuilder "github.com/tembuilderlabs/tembuilder-sdk/go"

client, err := tembuilder.New() // TEMBUILDER_API_KEY, or tembuilder.WithAPIKey(...)
if err != nil {
	return err
}
template, err := client.Templates.Get(ctx, "invoice", tembuilder.GetTemplateParams{})
if err != nil {
	return err
}
parameters := template.Input.ExampleParameters
parameters["customer"] = "Acme Corp"

status, err := client.Renders.CreateAndWait(ctx, tembuilder.RenderRequest{
	TemplateId: template.Id,
	Parameters: &parameters,
}, tembuilder.WaitOptions{})
if err != nil {
	return err
}
file, err := client.Renders.Download(ctx, status.RenderId.String())
if err != nil {
	return err
}
return os.WriteFile(file.Filename, file.Content, 0o644)
```

Iterate every page with range-over-func:

```go
for template, err := range client.Templates.All(ctx, tembuilder.ListTemplatesParams{}) {
	if err != nil {
		return err
	}
	fmt.Println(template.Slug)
}
```

## Rendering: pick the flow that fits

A render is a background job. `Renders.Create` returns a render id within
milliseconds; the PDF is produced afterwards. No call keeps a connection open
while the PDF renders, so choose by where your code runs:

| Flow | Use it for |
| --- | --- |
| 1. Create, then wait | Scripts, CLIs, cron jobs |
| 2. Create now, check later | HTTP handlers and job queues: store the id, return at once |
| 3. Create, get a webhook | Servers: Tembuilder calls you when the render ends |

### 1. Create, then wait

`CreateAndWait` = `Create` + `WaitFor`. It polls the status every second
(`PollInterval`) for up to two minutes (`Timeout`); `ctx` cancels it.

```go
status, err := client.Renders.CreateAndWait(ctx, tembuilder.RenderRequest{
	TemplateId: template.Id,
	Parameters: &parameters,
}, tembuilder.WaitOptions{PollInterval: 2 * time.Second, Timeout: time.Minute})
if err != nil {
	return err
}
file, err := client.Renders.Download(ctx, status.RenderId.String())
```

Already have a render id? `client.Renders.WaitFor(ctx, renderID, tembuilder.WaitOptions{})`.

### 2. Create now, check later

```go
// In the HTTP handler: queue the render and answer immediately.
queued, err := client.Renders.Create(ctx, tembuilder.RenderRequest{
	TemplateId: template.Id,
	Parameters: &parameters,
})
if err != nil {
	return err
}
renderID := queued.RenderId.String() // keep the id, e.g. on the order row

// Later (another request, a job, a "check status" button):
status, err := client.Renders.Get(ctx, renderID)
if err != nil {
	return err
}
switch status.Status {
case tembuilder.RenderStatusPending:
	// not ready yet: check again later
case tembuilder.RenderStatusSuccess:
	file, err := client.Renders.Download(ctx, renderID)
	if err != nil {
		return err
	}
	return os.WriteFile(file.Filename, file.Content, 0o644)
default: // failed or quota_exceeded
	return fmt.Errorf("render %s", status.Status)
}
```

Right after `Create`, `Renders.Get` can return an `*APIError` with status
404 for a moment while the job is being registered; treat it like pending.
`Renders.List` with `Status: &pending` (a `tembuilder.ListRendersParamsStatus`
set to `"pending"`) returns every render still running.

### 3. Create, get a webhook

Add a webhook endpoint in the Tembuilder app (**Webhooks** in the project sidebar), then
create renders as in flow 2 and download when the `renders.status` event
arrives (see [Webhooks](#webhooks)):

```go
if event.Type == "renders.status" && data.Status == tembuilder.RenderStatusSuccess {
	file, err := client.Renders.Download(ctx, data.RenderId.String())
}
```

## Options

`WithAPIKey`, `WithBaseURL`, `WithTimeout` (per call, retries included, default 60s),
`WithMaxRetries` (2), `WithRetryDelays` (500ms, 8s), `WithHTTPClient`.

Retries follow the same rules as every Tembuilder SDK: GETs on transport
errors and 429/502/503/504; `Renders.Create` only on 429/503 and never after
a transport error.

## Errors

`*APIError` (`StatusCode`, `Code`, `Description`, `Details`,
`RetryAfterSeconds`), `*ConnectionError`, `*TimeoutError`,
`*RenderFailedError`, `*RenderTimeoutError`; `IsNotFound(err)`. Webhook
failures wrap `ErrWebhookVerification`.

## Webhooks

```go
body, _ := io.ReadAll(r.Body)
event, err := tembuilder.VerifyWebhook(body, r.Header, secret, tembuilder.VerifyOptions{})
if err != nil {
	http.Error(w, "invalid signature", http.StatusBadRequest)
	return
}
if event.Type == "renders.status" {
	var data tembuilder.RenderStatusEventData
	_ = json.Unmarshal(event.Data, &data)
}
```

## Versioning

The SDK follows [Semantic Versioning](https://semver.org). Before 1.0, a minor
release may contain breaking changes; patch releases never do. Each release
is tagged in this repository and listed in the changelog.

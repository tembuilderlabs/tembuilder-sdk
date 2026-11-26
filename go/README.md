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

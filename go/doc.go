// Package tembuilder is the official Go SDK for the Tembuilder PDF rendering API.
//
//	client, err := tembuilder.New(tembuilder.WithAPIKey(os.Getenv("TEMBUILDER_API_KEY")))
//	status, err := client.Renders.CreateAndWait(ctx, tembuilder.RenderRequest{
//		TemplateId: templateID,
//		Parameters: &map[string]any{"customer": "Acme"},
//	}, tembuilder.WaitOptions{})
//	file, err := client.Renders.Download(ctx, status.RenderId.String())
//
// The low-level client in internal/api is generated from openapi/tembuilder.yaml;
// this package adds configuration, retries, error mapping, render polling,
// pagination and webhook verification on top of it.
package tembuilder

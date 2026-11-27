// Command quickstart mirrors the README; it is compiled in CI so the docs stay correct.
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"

	tembuilder "github.com/tembuilderlabs/tembuilder-sdk/go"
)

func run(ctx context.Context) error {
	client, err := tembuilder.New()
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
	file, err := client.Renders.DownloadFrom(ctx, status)
	if err != nil {
		return err
	}
	if err := os.WriteFile(file.Filename, file.Content, 0o644); err != nil {
		return err
	}

	for template, err := range client.Templates.All(ctx, tembuilder.ListTemplatesParams{}) {
		if err != nil {
			return err
		}
		fmt.Println(template.Slug)
	}
	return nil
}

func webhookHandler(secret string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		body, _ := io.ReadAll(r.Body)
		event, err := tembuilder.VerifyWebhook(body, r.Header, secret, tembuilder.VerifyOptions{})
		if err != nil {
			http.Error(w, "invalid signature", http.StatusBadRequest)
			return
		}
		if event.Type == "renders.status" {
			var data tembuilder.RenderStatusEventData
			_ = json.Unmarshal(event.Data, &data)
			log.Println(data.RenderId, data.Status)
		}
		w.WriteHeader(http.StatusNoContent)
	}
}

func main() {
	http.Handle("/webhooks/tembuilder", webhookHandler(os.Getenv("TEMBUILDER_WEBHOOK_SECRET")))
	if err := run(context.Background()); err != nil {
		log.Fatal(err)
	}
}

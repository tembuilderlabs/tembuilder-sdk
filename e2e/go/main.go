// Command e2e is a fresh consumer app for the Go SDK. e2e/run.sh creates an
// empty module, requires the SDK (the local checkout or a published tag) and
// runs it, so it proves the module as users get it: version, webhooks and,
// with TEMBUILDER_API_KEY, TEMBUILDER_BASE_URL and TEMBUILDER_SMOKE_TEMPLATE,
// a real render.
package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"os"
	"slices"
	"strings"
	"time"

	tembuilder "github.com/tembuilderlabs/tembuilder-sdk/go"
)

func step(name string) { fmt.Println("- " + name) }

func check(condition bool, format string, args ...any) {
	if !condition {
		log.Fatalf("FAIL: "+format, args...)
	}
}

func must[T any](value T, err error) T {
	if err != nil {
		log.Fatalf("FAIL: %v", err)
	}
	return value
}

func offline() {
	step("installed version " + tembuilder.Version)
	if expected := os.Getenv("EXPECTED_VERSION"); expected != "" {
		check(tembuilder.Version == expected, "version %s != %s", tembuilder.Version, expected)
	}

	step("webhook signature vectors")
	var contract struct {
		Secret  string `json:"secret"`
		Vectors []struct {
			Name      string `json:"name"`
			Timestamp string `json:"timestamp"`
			Signature string `json:"signature"`
			Body      string `json:"body"`
			Now       int64  `json:"now"`
			Valid     bool   `json:"valid"`
		} `json:"vectors"`
	}
	check(json.Unmarshal(must(os.ReadFile(os.Getenv("WEBHOOK_VECTORS"))), &contract) == nil, "read webhook vectors")
	for _, vector := range contract.Vectors {
		header := http.Header{}
		header.Set("Tembuilder-Timestamp", vector.Timestamp)
		header.Set("Tembuilder-Signature", vector.Signature)
		_, err := tembuilder.VerifyWebhook([]byte(vector.Body), header, contract.Secret, tembuilder.VerifyOptions{Now: time.Unix(vector.Now, 0)})
		check((err == nil) == vector.Valid, "%s: err=%v", vector.Name, err)
	}
}

func live(ctx context.Context) {
	client := must(tembuilder.New())

	step("account")
	must(client.Account.Get(ctx))

	step("template detail and input contract")
	template := must(client.Templates.Get(ctx, os.Getenv("TEMBUILDER_SMOKE_TEMPLATE"), tembuilder.GetTemplateParams{}))
	check(len(template.PublishedVersions) > 0, "smoke template has no published version")
	version := template.PublishedVersions[len(template.PublishedVersions)-1]
	detail := must(client.Templates.Get(ctx, template.Id.String(), tembuilder.GetTemplateParams{Version: tembuilder.Ptr(version)}))
	check(detail.Input.Version == version, "input version %d != %d", detail.Input.Version, version)

	step("template list contains it")
	found := false
	for item, err := range client.Templates.All(ctx, tembuilder.ListTemplatesParams{Search: tembuilder.Ptr(template.Slug)}) {
		must(item, err)
		found = found || item.Id == template.Id
	}
	check(found, "template list does not contain the smoke template")

	step("render, wait and download")
	parameters := detail.Input.ExampleParameters
	status := must(client.Renders.CreateAndWait(ctx, tembuilder.RenderRequest{
		TemplateId: template.Id,
		Version:    tembuilder.Ptr(version),
		Parameters: &parameters,
	}, tembuilder.WaitOptions{PollInterval: 2 * time.Second, Timeout: 3 * time.Minute}))
	check(status.FileUrl != nil && strings.HasPrefix(*status.FileUrl, "http"), "status has no signed file_url")

	step("download from the signed file_url, then by id through the API")
	signed := must(client.Renders.DownloadFrom(ctx, status))
	check(bytes.HasPrefix(signed.Content, []byte("%PDF-")), "signed download is not a PDF")
	viaAPI := must(client.Renders.Download(ctx, status.RenderId.String()))
	check(bytes.Equal(viaAPI.Content, signed.Content) && viaAPI.Filename == signed.Filename, "API download differs from the signed download")

	step("render log contains it")
	page := must(client.Renders.List(ctx, tembuilder.ListRendersParams{TemplateId: &template.Id, PerPage: tembuilder.Ptr(int32(20))}))
	check(slices.ContainsFunc(page.Data, func(render tembuilder.Render) bool { return render.Id == status.RenderId }), "render log does not contain the render")

	step("typed errors: unknown template is 404, bad key is 401")
	var apiErr *tembuilder.APIError
	_, err := client.Templates.Get(ctx, "e2e-template-that-does-not-exist", tembuilder.GetTemplateParams{})
	check(errors.As(err, &apiErr) && apiErr.StatusCode == http.StatusNotFound, "unknown template: %v", err)
	bad := must(tembuilder.New(tembuilder.WithAPIKey("invalid")))
	_, err = bad.Account.Get(ctx)
	check(errors.As(err, &apiErr) && apiErr.StatusCode == http.StatusUnauthorized && apiErr.Code == "COMMON_UNAUTHENTICATED", "bad key: %v", err)
}

func main() {
	offline()
	for _, name := range []string{"TEMBUILDER_API_KEY", "TEMBUILDER_BASE_URL", "TEMBUILDER_SMOKE_TEMPLATE"} {
		if os.Getenv(name) == "" {
			check(os.Getenv("REQUIRE_LIVE") != "1", "REQUIRE_LIVE=1 but %s is not set", name)
			fmt.Println("live API: skipped (TEMBUILDER_API_KEY, TEMBUILDER_BASE_URL, TEMBUILDER_SMOKE_TEMPLATE not set)")
			fmt.Println("go e2e ok")
			return
		}
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
	defer cancel()
	live(ctx)
	fmt.Println("go e2e ok (live)")
}

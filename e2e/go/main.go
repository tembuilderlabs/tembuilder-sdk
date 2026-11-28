// Command e2e is a fresh consumer app for the Go SDK. e2e/run.sh creates an
// empty module, requires the SDK (the local checkout or a published tag) and
// runs it, so it proves the module as users get it: version, webhooks and,
// with TEMBUILDER_API_KEY, TEMBUILDER_BASE_URL, TEMBUILDER_SMOKE_TEMPLATE and
// TEMBUILDER_PARAMETER_TEMPLATE, real renders.
package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"maps"
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

	liveParameters(ctx, client)

	step("typed errors: unknown template is 404, bad key is 401")
	var apiErr *tembuilder.APIError
	_, err := client.Templates.Get(ctx, "e2e-template-that-does-not-exist", tembuilder.GetTemplateParams{})
	check(errors.As(err, &apiErr) && apiErr.StatusCode == http.StatusNotFound, "unknown template: %v", err)
	bad := must(tembuilder.New(tembuilder.WithAPIKey("invalid")))
	_, err = bad.Account.Get(ctx)
	check(errors.As(err, &apiErr) && apiErr.StatusCode == http.StatusUnauthorized && apiErr.Code == "COMMON_UNAUTHENTICATED", "bad key: %v", err)
}

// liveParameters renders the imported e2e/parameter-template with every
// parameter type, with defaults only, and with a wrongly typed parameter.
func liveParameters(ctx context.Context, client *tembuilder.Client) {
	var cases struct {
		Valid   map[string]any `json:"valid"`
		Invalid map[string]any `json:"invalid"`
	}
	check(json.Unmarshal(must(os.ReadFile(os.Getenv("PARAMETER_CASES"))), &cases) == nil, "parameter cases are not JSON")
	template := must(client.Templates.Get(ctx, os.Getenv("TEMBUILDER_PARAMETER_TEMPLATE"), tembuilder.GetTemplateParams{}))
	check(len(template.PublishedVersions) > 0, "parameter template has no published version")
	version := tembuilder.Ptr(template.PublishedVersions[len(template.PublishedVersions)-1])
	wait := tembuilder.WaitOptions{PollInterval: 2 * time.Second, Timeout: 3 * time.Minute}
	isPDF := func(status *tembuilder.RenderStatus) bool {
		return bytes.HasPrefix(must(client.Renders.DownloadFrom(ctx, status)).Content, []byte("%PDF-"))
	}

	step("every parameter type renders (text, number, boolean, array, nested object)")
	typed := must(client.Renders.CreateAndWait(ctx, tembuilder.RenderRequest{TemplateId: template.Id, Version: version, Parameters: &cases.Valid}, wait))
	check(isPDF(typed), "typed render is not a PDF")

	step("omitted parameters fall back to their defaults")
	defaults := must(client.Renders.CreateAndWait(ctx, tembuilder.RenderRequest{TemplateId: template.Id, Version: version}, wait))
	check(isPDF(defaults), "defaults render is not a PDF")

	step("a parameter of the wrong type is rejected, not rendered")
	wrong := maps.Clone(cases.Valid)
	maps.Copy(wrong, cases.Invalid)
	_, err := client.Renders.CreateAndWait(ctx, tembuilder.RenderRequest{TemplateId: template.Id, Version: version, Parameters: &wrong}, wait)
	var failed *tembuilder.RenderFailedError
	var apiErr *tembuilder.APIError
	check((errors.As(err, &failed) && failed.Render.Status == tembuilder.RenderStatusFailed) ||
		(errors.As(err, &apiErr) && apiErr.StatusCode >= 400 && apiErr.StatusCode < 500),
		"wrongly typed parameter: %v", err)
}

func main() {
	offline()
	for _, name := range []string{"TEMBUILDER_API_KEY", "TEMBUILDER_BASE_URL", "TEMBUILDER_SMOKE_TEMPLATE", "TEMBUILDER_PARAMETER_TEMPLATE"} {
		if os.Getenv(name) == "" {
			check(os.Getenv("REQUIRE_LIVE") != "1", "REQUIRE_LIVE=1 but %s is not set", name)
			fmt.Println("live API: skipped (TEMBUILDER_API_KEY, TEMBUILDER_BASE_URL, TEMBUILDER_SMOKE_TEMPLATE, TEMBUILDER_PARAMETER_TEMPLATE not set)")
			fmt.Println("go e2e ok")
			return
		}
	}
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Minute)
	defer cancel()
	live(ctx)
	fmt.Println("go e2e ok (live)")
}

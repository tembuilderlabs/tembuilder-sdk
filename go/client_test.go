package tembuilder

import (
	"context"
	"errors"
	"net/http"
	"strings"
	"testing"
	"time"

	"github.com/google/uuid"
)

const renderID = "5a6b7c8d-1e2f-4a3b-8c4d-5e6f7a8b9c0d"
const templateID = "7d0f5a2e-1c3b-4d5e-9f80-a1b2c3d4e5f6"

var (
	notFound = jsonHandler(404, map[string]any{"code": "RENDER_NOT_FOUND", "description": "render not found", "details": []string{}})
	queued   = jsonHandler(202, map[string]any{"render_id": renderID, "status": "queued", "status_url": "/v1/renders/" + renderID})
)

func statusHandler(status string, extra ...string) http.HandlerFunc {
	body := map[string]any{"render_id": renderID, "status": status}
	for i := 0; i+1 < len(extra); i += 2 {
		body[extra[i]] = extra[i+1]
	}
	return jsonHandler(200, body)
}

func templatePage(slugs []string, more bool) http.HandlerFunc {
	data := []map[string]any{}
	for _, slug := range slugs {
		data = append(data, map[string]any{"id": templateID, "slug": slug, "name": "T", "current_version": 1, "status": "published", "published_versions": []int{1}, "created_at": nil, "updated_at": nil})
	}
	return jsonHandler(200, map[string]any{"data": data, "page": 1, "per_page": 1, "has_more": more})
}

func renderPage(ids []string, more bool) http.HandlerFunc {
	data := []map[string]any{}
	for _, id := range ids {
		data = append(data, map[string]any{"id": renderID, "short_id": id, "status": "success", "template_id": templateID, "template_version": 1, "variant": nil, "duration_ms": nil, "error_message": nil, "started_at": "2026-11-20T08:30:00Z", "completed_at": nil, "status_url": "/s", "download_url": nil})
	}
	return jsonHandler(200, map[string]any{"data": data, "page": 1, "per_page": 1, "has_more": more})
}

func TestNewConfiguration(t *testing.T) {
	t.Setenv("TEMBUILDER_API_KEY", "")
	t.Setenv("TEMBUILDER_BASE_URL", "")
	if _, err := New(); err == nil || !strings.Contains(err.Error(), "API key is required") {
		t.Fatalf("err = %v", err)
	}

	server := newStub(t, jsonHandler(200, map[string]any{}))
	t.Setenv("TEMBUILDER_API_KEY", "env-key")
	t.Setenv("TEMBUILDER_BASE_URL", server.URL+"//")
	client, err := New()
	if err != nil {
		t.Fatal(err)
	}
	if _, err := client.Account.Get(context.Background()); err != nil {
		t.Fatal(err)
	}
	sent := server.requests[0]
	if sent.Path != "/v1/me" || sent.Header.Get("ApiKey") != "env-key" || sent.Header.Get("User-Agent") != "tembuilder-go/"+Version {
		t.Fatalf("%+v", sent)
	}

	t.Setenv("TEMBUILDER_BASE_URL", "")
	client, err = New(WithHTTPClient(&http.Client{Transport: roundTripper(func(r *http.Request) (*http.Response, error) {
		if r.URL.String() != DefaultBaseURL+"/v1/me" {
			t.Fatalf("url %s", r.URL)
		}
		return nil, errors.New("offline")
	})}), WithTimeout(time.Second), WithMaxRetries(0))
	if err != nil {
		t.Fatal(err)
	}
	var connErr *ConnectionError
	if _, err := client.Account.Get(context.Background()); !errors.As(err, &connErr) {
		t.Fatalf("err = %v", err)
	}
}

type roundTripper func(*http.Request) (*http.Response, error)

func (f roundTripper) RoundTrip(r *http.Request) (*http.Response, error) { return f(r) }

func TestUnexpectedSuccessBodies(t *testing.T) {
	server := newStub(t, func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "text/plain")
		_, _ = w.Write([]byte("ok"))
	})
	client := newTestClient(t, server)
	ctx := context.Background()
	if _, err := client.Account.Get(ctx); err == nil || !strings.Contains(err.Error(), "unexpected response body for HTTP 200") {
		t.Fatalf("err = %v", err)
	}
	checks := []func() error{
		func() error { _, err := client.Templates.List(ctx, ListTemplatesParams{}); return err },
		func() error { _, err := client.Templates.Get(ctx, "x", GetTemplateParams{}); return err },
		func() error { _, err := client.Renders.Create(ctx, RenderRequest{}); return err },
		func() error { _, err := client.Renders.Get(ctx, renderID); return err },
		func() error { _, err := client.Renders.List(ctx, ListRendersParams{}); return err },
	}
	for i, check := range checks {
		if err := check(); err == nil {
			t.Fatalf("check %d accepted a non-JSON body", i)
		}
	}

	broken := newStub(t, func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte("{"))
	})
	if _, err := newTestClient(t, broken).Account.Get(ctx); err == nil || !strings.Contains(err.Error(), "decode response") {
		t.Fatalf("err = %v", err)
	}
}

func TestErrorPropagationFromEveryCall(t *testing.T) {
	server := newStub(t, jsonHandler(403, map[string]any{"code": "COMMON_FORBIDDEN", "description": "no", "details": []string{}}))
	client := newTestClient(t, server)
	ctx := context.Background()
	calls := []func() error{
		func() error { _, err := client.Templates.Get(ctx, "x", GetTemplateParams{}); return err },
		func() error { _, err := client.Renders.Download(ctx, renderID); return err },
		func() error { _, err := client.Renders.CreateAndWait(ctx, RenderRequest{}, WaitOptions{}); return err },
		func() error {
			for _, err := range client.Templates.All(ctx, ListTemplatesParams{}) {
				return err
			}
			return nil
		},
		func() error {
			for _, err := range client.Renders.All(ctx, ListRendersParams{}) {
				return err
			}
			return nil
		},
	}
	for i, call := range calls {
		var apiErr *APIError
		if err := call(); !errors.As(err, &apiErr) || apiErr.StatusCode != 403 {
			t.Fatalf("call %d: err = %v", i, err)
		}
	}
}

func TestPagination(t *testing.T) {
	ctx := context.Background()
	server := newStub(t, templatePage([]string{"a", "b"}, true), templatePage([]string{"c"}, false))
	var slugs []string
	for template, err := range newTestClient(t, server).Templates.All(ctx, ListTemplatesParams{PerPage: Ptr(int32(2))}) {
		if err != nil {
			t.Fatal(err)
		}
		slugs = append(slugs, template.Slug)
	}
	if strings.Join(slugs, ",") != "a,b,c" || server.requests[1].Query["page"] != "2" || server.requests[1].Query["per_page"] != "2" {
		t.Fatalf("slugs %v requests %+v", slugs, server.requests)
	}

	renders := newStub(t, renderPage([]string{"a"}, true), renderPage([]string{"b"}, false))
	var ids []string
	for render, err := range newTestClient(t, renders).Renders.All(ctx, ListRendersParams{}) {
		if err != nil {
			t.Fatal(err)
		}
		ids = append(ids, render.ShortId)
	}
	if strings.Join(ids, ",") != "a,b" {
		t.Fatal(ids)
	}

	stopEarly := newStub(t, templatePage([]string{"a", "b"}, true))
	for range newTestClient(t, stopEarly).Templates.All(ctx, ListTemplatesParams{}) {
		break
	}
	if stopEarly.count() != 1 {
		t.Fatalf("iteration continued after break: %d requests", stopEarly.count())
	}
}

func TestDownloadDefaults(t *testing.T) {
	server := newStub(t, func(w http.ResponseWriter, _ *http.Request) {
		w.Header()["Content-Type"] = nil
		_, _ = w.Write([]byte("%P"))
	})
	file, err := newTestClient(t, server).Renders.Download(context.Background(), renderID)
	if err != nil || string(file.Content) != "%P" || file.ContentType != "application/pdf" || file.Filename != "" {
		t.Fatalf("file %+v err %v", file, err)
	}
}

func TestFilenameFromDisposition(t *testing.T) {
	for header, want := range map[string]string{
		"":                                  "",
		"inline":                            "",
		`attachment; filename="report.pdf"`: "report.pdf",
		"attachment; filename*=UTF-8''h%C3%B3a-%C4%91%C6%A1n.pdf": "hóa-đơn.pdf",
		"attachment; filename=":                                   "",
	} {
		h := http.Header{}
		h.Set("Content-Disposition", header)
		if got := filenameFromDisposition(h); got != want {
			t.Fatalf("%q: got %q want %q", header, got, want)
		}
	}
}

func TestWaitFor(t *testing.T) {
	ctx := context.Background()
	fast := WaitOptions{PollInterval: time.Millisecond}

	server := newStub(t, notFound, statusHandler("pending"), statusHandler("success"))
	status, err := newTestClient(t, server).Renders.WaitFor(ctx, renderID, fast)
	if err != nil || status.Status != "success" || server.count() != 3 {
		t.Fatalf("status %+v err %v requests %d", status, err, server.count())
	}

	create := newStub(t, queued, statusHandler("success"))
	if status, err := newTestClient(t, create).Renders.CreateAndWait(ctx, RenderRequest{TemplateId: uuid.MustParse(templateID)}, fast); err != nil || status.Status != "success" {
		t.Fatalf("status %+v err %v", status, err)
	}

	for _, terminal := range []string{"failed", "quota_exceeded"} {
		failing := newStub(t, statusHandler(terminal, "error_message", "boom"))
		var failed *RenderFailedError
		if _, err := newTestClient(t, failing).Renders.WaitFor(ctx, renderID, WaitOptions{}); !errors.As(err, &failed) || failed.Render.Status != terminal {
			t.Fatalf("%s: err = %v", terminal, err)
		}
	}

	pending := newStub(t, statusHandler("pending"))
	var timedOut *RenderTimeoutError
	if _, err := newTestClient(t, pending).Renders.WaitFor(ctx, renderID, WaitOptions{PollInterval: time.Millisecond, Timeout: 10 * time.Millisecond}); !errors.As(err, &timedOut) || timedOut.LastStatus.Status != "pending" || timedOut.RenderID != renderID ||
		timedOut.Error() != "tembuilder: render "+renderID+" did not finish before the deadline (last status: pending)" {
		t.Fatalf("err = %v", err)
	}

	missing := newStub(t, notFound)
	if _, err := newTestClient(t, missing).Renders.WaitFor(ctx, renderID, WaitOptions{NotFoundGrace: time.Nanosecond}); !IsNotFound(err) {
		t.Fatalf("err = %v", err)
	}

	deadline, cancel := context.WithTimeout(ctx, 20*time.Millisecond)
	defer cancel()
	sleeping := newStub(t, statusHandler("pending"))
	if _, err := newTestClient(t, sleeping).Renders.WaitFor(deadline, renderID, WaitOptions{PollInterval: time.Hour}); !errors.Is(err, context.DeadlineExceeded) || sleeping.count() != 1 {
		t.Fatalf("err = %v requests %d", err, sleeping.count())
	}
}

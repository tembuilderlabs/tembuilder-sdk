package tembuilder

import (
	"context"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

var accountBody = map[string]any{"api_key_id": renderID, "workspace_id": renderID, "project": map[string]any{"id": renderID, "name": "B", "slug": "b"}, "scopes": []string{}}

func retrying() []Option {
	return []Option{WithMaxRetries(2), WithRetryDelays(time.Millisecond, 2*time.Millisecond)}
}

func TestRetriesTransientGETStatuses(t *testing.T) {
	for _, status := range []int{429, 502, 503, 504} {
		server := newStub(t, jsonHandler(status, map[string]any{}), jsonHandler(200, accountBody))
		if _, err := newTestClient(t, server, retrying()...).Account.Get(context.Background()); err != nil || server.count() != 2 {
			t.Fatalf("%d: err %v requests %d", status, err, server.count())
		}
	}
}

func TestRetryAfterIsCapped(t *testing.T) {
	server := newStub(t, jsonHandler(503, map[string]any{}, "Retry-After", "120"), jsonHandler(200, accountBody))
	started := time.Now()
	if _, err := newTestClient(t, server, retrying()...).Account.Get(context.Background()); err != nil || time.Since(started) > time.Second {
		t.Fatalf("err %v after %s", err, time.Since(started))
	}
}

func TestPOSTRetryRules(t *testing.T) {
	ctx := context.Background()
	request := RenderRequest{Parameters: &map[string]any{"a": 1.0}}
	busy := newStub(t, jsonHandler(503, map[string]any{"code": "COMMON_UNAVAILABLE", "description": "busy", "details": []string{}}), queued)
	if _, err := newTestClient(t, busy, retrying()...).Renders.Create(ctx, request); err != nil || busy.count() != 2 || string(busy.requests[0].Body) != string(busy.requests[1].Body) {
		t.Fatalf("err %v requests %+v", err, busy.requests)
	}

	gateway := newStub(t, jsonHandler(502, map[string]any{}))
	if _, err := newTestClient(t, gateway, retrying()...).Renders.Create(ctx, request); err == nil || gateway.count() != 1 {
		t.Fatalf("err %v requests %d", err, gateway.count())
	}

	exhausted := newStub(t, jsonHandler(503, map[string]any{"code": "COMMON_UNAVAILABLE", "description": "busy", "details": []string{}}))
	var apiErr *APIError
	if _, err := newTestClient(t, exhausted, retrying()...).Account.Get(ctx); !errors.As(err, &apiErr) || exhausted.count() != 3 {
		t.Fatalf("err %v requests %d", err, exhausted.count())
	}
}

func TestNetworkErrorRetryRules(t *testing.T) {
	calls := 0
	flaky := roundTripper(func(r *http.Request) (*http.Response, error) {
		calls++
		if calls == 1 {
			return nil, errors.New("reset")
		}
		recorder := httptest.NewRecorder()
		jsonHandler(200, accountBody)(recorder, r)
		return recorder.Result(), nil
	})
	client, _ := New(append(retrying(), WithAPIKey("k"), WithHTTPClient(&http.Client{Transport: flaky}))...)
	if _, err := client.Account.Get(context.Background()); err != nil || calls != 2 {
		t.Fatalf("err %v calls %d", err, calls)
	}

	calls = 0
	down := roundTripper(func(*http.Request) (*http.Response, error) { calls++; return nil, errors.New("reset") })
	client, _ = New(append(retrying(), WithAPIKey("k"), WithHTTPClient(&http.Client{Transport: down}))...)
	var connErr *ConnectionError
	if _, err := client.Renders.Create(context.Background(), RenderRequest{}); !errors.As(err, &connErr) || calls != 1 {
		t.Fatalf("err %v calls %d", err, calls)
	}
}

func TestTimeoutsAndCancellation(t *testing.T) {
	block := make(chan struct{})
	t.Cleanup(func() { close(block) })
	slow := newStub(t, func(w http.ResponseWriter, r *http.Request) {
		select {
		case <-block:
		case <-r.Context().Done():
		}
	})
	var timeoutErr *TimeoutError
	if _, err := newTestClient(t, slow, WithTimeout(20*time.Millisecond)).Account.Get(context.Background()); !errors.As(err, &timeoutErr) {
		t.Fatalf("err = %v", err)
	}

	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if _, err := newTestClient(t, slow).Account.Get(ctx); !errors.Is(err, context.Canceled) {
		t.Fatalf("err = %v", err)
	}
}

func TestRetryTransportInternals(t *testing.T) {
	cancelled := func(*http.Request, time.Duration) error { return context.Canceled }
	transport := &retryTransport{maxRetries: 1, baseDelay: time.Millisecond, maxDelay: time.Millisecond, random: func() float64 { return 1 }, sleep: cancelled}

	transport.base = roundTripper(func(*http.Request) (*http.Response, error) { return nil, errors.New("reset") })
	request, _ := http.NewRequest(http.MethodGet, "https://api.test/v1/me", nil)
	if _, err := transport.RoundTrip(request); !errors.Is(err, context.Canceled) {
		t.Fatalf("err = %v", err)
	}

	transport.base = roundTripper(func(*http.Request) (*http.Response, error) {
		return &http.Response{StatusCode: 503, Header: http.Header{}, Body: io.NopCloser(strings.NewReader(""))}, nil
	})
	if _, err := transport.RoundTrip(request); !errors.Is(err, context.Canceled) {
		t.Fatalf("err = %v", err)
	}

	transport.sleep = func(*http.Request, time.Duration) error { return nil }
	post, _ := http.NewRequest(http.MethodPost, "https://api.test/v1/pdf/render", strings.NewReader("{}"))
	post.GetBody = func() (io.ReadCloser, error) { return nil, errors.New("body gone") }
	if _, err := transport.RoundTrip(post); err == nil || err.Error() != "body gone" {
		t.Fatalf("err = %v", err)
	}

	if got := transport.delay(0, -1); got != time.Millisecond {
		t.Fatalf("delay %s", got)
	}
	if got := transport.delay(0, 30); got != time.Millisecond {
		t.Fatalf("capped delay %s", got)
	}
	if value := defaultRandom(); value < 0 || value >= 1 {
		t.Fatalf("random %f", value)
	}
}

func TestSleepContext(t *testing.T) {
	request, _ := http.NewRequest(http.MethodGet, "https://api.test", nil)
	if err := sleepContext(request, time.Millisecond); err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if err := sleepContext(request.WithContext(ctx), time.Hour); !errors.Is(err, context.Canceled) {
		t.Fatalf("err = %v", err)
	}
}

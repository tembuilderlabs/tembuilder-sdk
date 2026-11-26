package tembuilder

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"sync"
	"testing"
	"time"
)

func loadContract(t *testing.T, name string, target any) {
	t.Helper()
	data, err := os.ReadFile(filepath.Join("..", "contract", name))
	if err != nil {
		t.Fatal(err)
	}
	if err := json.Unmarshal(data, target); err != nil {
		t.Fatal(err)
	}
}

type recordedRequest struct {
	Method string
	Path   string
	Query  map[string]string
	Header http.Header
	Body   []byte
}

// stubServer answers from a handler queue (the last handler repeats) and
// records every request.
type stubServer struct {
	*httptest.Server
	mu       sync.Mutex
	handlers []http.HandlerFunc
	requests []recordedRequest
}

func newStub(t *testing.T, handlers ...http.HandlerFunc) *stubServer {
	t.Helper()
	stub := &stubServer{handlers: handlers}
	stub.Server = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		body, _ := io.ReadAll(r.Body)
		query := map[string]string{}
		for key := range r.URL.Query() {
			query[key] = r.URL.Query().Get(key)
		}
		stub.mu.Lock()
		stub.requests = append(stub.requests, recordedRequest{r.Method, r.URL.Path, query, r.Header.Clone(), body})
		handler := stub.handlers[min(len(stub.requests)-1, len(stub.handlers)-1)]
		stub.mu.Unlock()
		handler(w, r)
	}))
	t.Cleanup(stub.Close)
	return stub
}

func (s *stubServer) count() int {
	s.mu.Lock()
	defer s.mu.Unlock()
	return len(s.requests)
}

func jsonHandler(status int, body any, headers ...string) http.HandlerFunc {
	return func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		for i := 0; i+1 < len(headers); i += 2 {
			w.Header().Set(headers[i], headers[i+1])
		}
		w.WriteHeader(status)
		_ = json.NewEncoder(w).Encode(body)
	}
}

func newTestClient(t *testing.T, server *stubServer, options ...Option) *Client {
	t.Helper()
	defaults := []Option{WithAPIKey("test-key"), WithBaseURL(server.URL), WithMaxRetries(0), WithRetryDelays(time.Millisecond, 2*time.Millisecond)}
	client, err := New(append(defaults, options...)...)
	if err != nil {
		t.Fatal(err)
	}
	return client
}

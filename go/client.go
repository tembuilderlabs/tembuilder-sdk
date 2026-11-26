package tembuilder

import (
	"context"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/tembuilderlabs/tembuilder-sdk/go/internal/api"
)

// DefaultBaseURL is the production API origin.
const DefaultBaseURL = "https://api.tembuilder.com"

type config struct {
	apiKey     string
	baseURL    string
	timeout    time.Duration
	maxRetries int
	baseDelay  time.Duration
	maxDelay   time.Duration
	httpClient *http.Client
}

// Option configures a Client.
type Option func(*config)

// WithAPIKey sets the project API key. Defaults to TEMBUILDER_API_KEY.
func WithAPIKey(key string) Option { return func(c *config) { c.apiKey = key } }

// WithBaseURL sets the API origin. Defaults to TEMBUILDER_BASE_URL, then DefaultBaseURL.
func WithBaseURL(url string) Option { return func(c *config) { c.baseURL = url } }

// WithTimeout bounds each call, retries included. Default 60s.
func WithTimeout(timeout time.Duration) Option { return func(c *config) { c.timeout = timeout } }

// WithMaxRetries sets how many times a transient failure is retried. Default 2.
func WithMaxRetries(retries int) Option { return func(c *config) { c.maxRetries = retries } }

// WithRetryDelays sets the exponential backoff base and the cap of a single wait.
// Defaults 500ms and 8s.
func WithRetryDelays(base, max time.Duration) Option {
	return func(c *config) { c.baseDelay, c.maxDelay = base, max }
}

// WithHTTPClient uses a custom http.Client; its Transport is wrapped with retries.
func WithHTTPClient(client *http.Client) Option { return func(c *config) { c.httpClient = client } }

// Client is the Tembuilder API client. It is safe for concurrent use.
type Client struct {
	Account   *AccountService
	Templates *TemplatesService
	Renders   *RendersService
}

// New creates a Client.
func New(options ...Option) (*Client, error) {
	cfg := config{
		apiKey:     os.Getenv("TEMBUILDER_API_KEY"),
		baseURL:    os.Getenv("TEMBUILDER_BASE_URL"),
		timeout:    60 * time.Second,
		maxRetries: 2,
		baseDelay:  500 * time.Millisecond,
		maxDelay:   8 * time.Second,
		httpClient: &http.Client{},
	}
	for _, option := range options {
		option(&cfg)
	}
	if cfg.apiKey == "" {
		return nil, errors.New("tembuilder: an API key is required: use WithAPIKey or set TEMBUILDER_API_KEY")
	}
	if cfg.baseURL == "" {
		cfg.baseURL = DefaultBaseURL
	}
	base := cfg.httpClient.Transport
	if base == nil {
		base = http.DefaultTransport
	}
	httpClient := *cfg.httpClient
	httpClient.Timeout = cfg.timeout
	httpClient.Transport = &retryTransport{
		base:       base,
		maxRetries: cfg.maxRetries,
		baseDelay:  cfg.baseDelay,
		maxDelay:   cfg.maxDelay,
		random:     defaultRandom,
		sleep:      sleepContext,
	}
	apiKey := cfg.apiKey
	generated := &api.Client{
		Server: strings.TrimRight(cfg.baseURL, "/") + "/",
		Client: &httpClient,
		RequestEditors: []api.RequestEditorFn{func(_ context.Context, request *http.Request) error {
			request.Header.Set("ApiKey", apiKey)
			request.Header.Set("User-Agent", "tembuilder-go/"+Version)
			return nil
		}},
	}
	return &Client{
		Account:   &AccountService{api: generated},
		Templates: &TemplatesService{api: generated},
		Renders:   &RendersService{api: generated},
	}, nil
}

// call turns a raw generated-client response into a parsed result or an
// error. Error statuses are handled here, before the generated parser, so a
// non-JSON error body is still reported as an APIError.
func call[R any](response *http.Response, err error, parse func(*http.Response) (R, error)) (R, error) {
	var zero R
	if err != nil {
		return zero, transportError(err)
	}
	if response.StatusCode < 200 || response.StatusCode > 299 {
		defer response.Body.Close()
		body, _ := io.ReadAll(response.Body)
		return zero, newAPIError(response, body)
	}
	parsed, err := parse(response)
	if err != nil {
		return zero, fmt.Errorf("tembuilder: decode response: %w", err)
	}
	return parsed, nil
}

func transportError(err error) error {
	if errors.Is(err, context.Canceled) {
		return err
	}
	var netErr net.Error
	if errors.Is(err, context.DeadlineExceeded) || (errors.As(err, &netErr) && netErr.Timeout()) {
		return &TimeoutError{Err: err}
	}
	return &ConnectionError{Err: err}
}

// required unwraps the parsed body for the documented success status.
func required[T any](value *T, status int) (*T, error) {
	if value == nil {
		return nil, fmt.Errorf("tembuilder: unexpected response body for HTTP %d", status)
	}
	return value, nil
}

// AccountService inspects the API key in use.
type AccountService struct{ api *api.Client }

// Get returns the project, workspace and scopes of the API key.
func (s *AccountService) Get(ctx context.Context) (*Account, error) {
	response, err := s.api.GetAccount(ctx)
	parsed, err := call(response, err, api.ParseGetAccountResponse)
	if err != nil {
		return nil, err
	}
	return required(parsed.JSON200, parsed.StatusCode())
}

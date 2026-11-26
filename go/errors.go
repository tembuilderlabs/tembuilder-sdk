package tembuilder

import (
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"strconv"
	"strings"
)

// APIError is a non-2xx API response. Branch on Code (stable, e.g.
// TEMPLATE_NOT_FOUND); Description is human-readable.
type APIError struct {
	StatusCode  int
	Code        string
	Description string
	Details     []string
	// RetryAfterSeconds is the Retry-After header value, or -1 when absent.
	RetryAfterSeconds int
}

func (e *APIError) Error() string {
	return fmt.Sprintf("tembuilder: %s (HTTP %d): %s", e.Code, e.StatusCode, e.Description)
}

// newAPIError builds an APIError from a response body. Bodies that are not
// the standard {code, description, details} shape still yield an HTTP_<status> code.
func newAPIError(response *http.Response, body []byte) *APIError {
	apiErr := &APIError{StatusCode: response.StatusCode, RetryAfterSeconds: parseRetryAfter(response.Header.Get("Retry-After"))}
	var standard struct {
		Code        *string `json:"code"`
		Description *string `json:"description"`
		Details     []any   `json:"details"`
	}
	if json.Unmarshal(body, &standard) == nil && standard.Code != nil && standard.Description != nil {
		apiErr.Code, apiErr.Description = *standard.Code, *standard.Description
		apiErr.Details = make([]string, 0, len(standard.Details))
		for _, detail := range standard.Details {
			apiErr.Details = append(apiErr.Details, fmt.Sprint(detail))
		}
		return apiErr
	}
	apiErr.Code = "HTTP_" + strconv.Itoa(response.StatusCode)
	apiErr.Description = strings.TrimSpace(string(body))
	if apiErr.Description == "" {
		apiErr.Description = http.StatusText(response.StatusCode)
	}
	if apiErr.Description == "" {
		apiErr.Description = "request failed"
	}
	apiErr.Details = []string{}
	return apiErr
}

// IsNotFound reports whether err is an APIError with status 404.
func IsNotFound(err error) bool {
	var apiErr *APIError
	return errors.As(err, &apiErr) && apiErr.StatusCode == http.StatusNotFound
}

// ConnectionError means the request never produced a response.
type ConnectionError struct{ Err error }

func (e *ConnectionError) Error() string { return "tembuilder: connection failed: " + e.Err.Error() }
func (e *ConnectionError) Unwrap() error { return e.Err }

// TimeoutError means the request exceeded the client timeout.
type TimeoutError struct{ Err error }

func (e *TimeoutError) Error() string { return "tembuilder: request timed out: " + e.Err.Error() }
func (e *TimeoutError) Unwrap() error { return e.Err }

// RenderFailedError means a render reached "failed" or "quota_exceeded".
type RenderFailedError struct{ Render RenderStatus }

func (e *RenderFailedError) Error() string {
	message := fmt.Sprintf("tembuilder: render %s ended with status %s", e.Render.RenderId, e.Render.Status)
	if e.Render.ErrorMessage != nil && *e.Render.ErrorMessage != "" {
		message += ": " + *e.Render.ErrorMessage
	}
	return message
}

// RenderTimeoutError means a render was not terminal before the wait deadline.
type RenderTimeoutError struct {
	RenderID   string
	LastStatus *RenderStatus
}

func (e *RenderTimeoutError) Error() string {
	last := "unknown"
	if e.LastStatus != nil {
		last = e.LastStatus.Status
	}
	return fmt.Sprintf("tembuilder: render %s did not finish before the deadline (last status: %s)", e.RenderID, last)
}

// ErrWebhookVerification is wrapped by every VerifyWebhook failure.
var ErrWebhookVerification = errors.New("tembuilder: webhook verification failed")

// parseRetryAfter parses delta-seconds; HTTP-dates and absence yield -1.
func parseRetryAfter(value string) int {
	value = strings.TrimSpace(value)
	seconds, err := strconv.Atoi(value)
	if err != nil || seconds < 0 || strings.HasPrefix(value, "+") {
		return -1
	}
	return seconds
}

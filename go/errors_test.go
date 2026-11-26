package tembuilder

import (
	"errors"
	"net/http"
	"testing"

	"github.com/google/uuid"
)

func TestNewAPIError(t *testing.T) {
	response := &http.Response{StatusCode: 503, Header: http.Header{"Retry-After": {"2"}}}
	apiErr := newAPIError(response, []byte(`{"code":"COMMON_UNAVAILABLE","description":"busy","details":["a",3]}`))
	if apiErr.Code != "COMMON_UNAVAILABLE" || apiErr.Description != "busy" || apiErr.RetryAfterSeconds != 2 ||
		len(apiErr.Details) != 2 || apiErr.Details[1] != "3" {
		t.Fatalf("%+v", apiErr)
	}
	if apiErr.Error() != "tembuilder: COMMON_UNAVAILABLE (HTTP 503): busy" {
		t.Fatal(apiErr.Error())
	}

	for _, tc := range []struct {
		status int
		body   string
		want   string
	}{
		{502, "  bad gateway  ", "bad gateway"},
		{500, "", "Internal Server Error"},
		{599, "", "request failed"},
		{500, `{"message":"x"}`, `{"message":"x"}`},
	} {
		apiErr := newAPIError(&http.Response{StatusCode: tc.status, Header: http.Header{}}, []byte(tc.body))
		if apiErr.Description != tc.want || apiErr.RetryAfterSeconds != -1 || apiErr.Code[:5] != "HTTP_" {
			t.Fatalf("%d %q: %+v", tc.status, tc.body, apiErr)
		}
	}
}

func TestParseRetryAfter(t *testing.T) {
	for value, want := range map[string]int{"": -1, "7": 7, " 3 ": 3, "Wed, 21 Oct 2015 07:28:00 GMT": -1, "-1": -1, "+5": -1} {
		if got := parseRetryAfter(value); got != want {
			t.Fatalf("%q: got %d want %d", value, got, want)
		}
	}
}

func TestErrorMessagesAndHelpers(t *testing.T) {
	id := uuid.MustParse("5a6b7c8d-1e2f-4a3b-8c4d-5e6f7a8b9c0d")
	message := "bad"
	if got := (&RenderFailedError{Render: RenderStatus{RenderId: id, Status: "failed", ErrorMessage: &message}}).Error(); got != "tembuilder: render "+id.String()+" ended with status failed: bad" {
		t.Fatal(got)
	}
	if got := (&RenderFailedError{Render: RenderStatus{RenderId: id, Status: "quota_exceeded"}}).Error(); got != "tembuilder: render "+id.String()+" ended with status quota_exceeded" {
		t.Fatal(got)
	}
	if got := (&RenderTimeoutError{RenderID: "r"}).Error(); got != "tembuilder: render r did not finish before the deadline (last status: unknown)" {
		t.Fatal(got)
	}
	cause := errors.New("boom")
	if err := (&ConnectionError{Err: cause}); !errors.Is(err, cause) || err.Error() != "tembuilder: connection failed: boom" {
		t.Fatal(err)
	}
	if err := (&TimeoutError{Err: cause}); !errors.Is(err, cause) || err.Error() != "tembuilder: request timed out: boom" {
		t.Fatal(err)
	}
	if IsNotFound(cause) || !IsNotFound(&APIError{StatusCode: 404}) {
		t.Fatal("IsNotFound")
	}
	if *Ptr(int32(3)) != 3 {
		t.Fatal("Ptr")
	}
}

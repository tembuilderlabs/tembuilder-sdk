package tembuilder

import (
	"io"
	"math"
	"math/rand/v2"
	"net/http"
	"time"
)

// retryTransport resends a request after a transient failure when that is
// safe: GETs after any transient failure, other methods only on 429/503,
// which mean the request was not processed (the render endpoint answers 503
// before admitting a job). A POST that failed without a response is never
// resent, because it may have been accepted.
type retryTransport struct {
	base       http.RoundTripper
	maxRetries int
	baseDelay  time.Duration
	maxDelay   time.Duration
	random     func() float64
	sleep      func(*http.Request, time.Duration) error
}

var (
	retryableStatuses    = map[int]bool{429: true, 503: true}
	retryableGetStatuses = map[int]bool{429: true, 502: true, 503: true, 504: true}
)

func (t *retryTransport) RoundTrip(request *http.Request) (*http.Response, error) {
	idempotent := request.Method == http.MethodGet || request.Method == http.MethodHead
	for attempt := 0; ; attempt++ {
		canRetry := attempt < t.maxRetries
		attemptRequest := request
		if attempt > 0 && request.GetBody != nil {
			body, err := request.GetBody()
			if err != nil {
				return nil, err
			}
			attemptRequest = request.Clone(request.Context())
			attemptRequest.Body = body
		}
		response, err := t.base.RoundTrip(attemptRequest)
		if err != nil {
			if canRetry && idempotent && request.Context().Err() == nil {
				if sleepErr := t.sleep(request, t.delay(attempt, -1)); sleepErr != nil {
					return nil, sleepErr
				}
				continue
			}
			return nil, err
		}
		retryable := retryableStatuses
		if idempotent {
			retryable = retryableGetStatuses
		}
		if canRetry && retryable[response.StatusCode] {
			retryAfter := parseRetryAfter(response.Header.Get("Retry-After"))
			_, _ = io.Copy(io.Discard, response.Body)
			_ = response.Body.Close()
			if sleepErr := t.sleep(request, t.delay(attempt, retryAfter)); sleepErr != nil {
				return nil, sleepErr
			}
			continue
		}
		return response, nil
	}
}

// delay prefers a server Retry-After (capped); otherwise exponential backoff
// with full jitter.
func (t *retryTransport) delay(attempt, retryAfterSeconds int) time.Duration {
	if retryAfterSeconds >= 0 {
		return min(time.Duration(retryAfterSeconds)*time.Second, t.maxDelay)
	}
	ceiling := math.Min(float64(t.baseDelay)*math.Pow(2, float64(attempt)), float64(t.maxDelay))
	return time.Duration(t.random() * ceiling)
}

// sleepContext waits d or until the request context ends.
func sleepContext(request *http.Request, d time.Duration) error {
	timer := time.NewTimer(d)
	defer timer.Stop()
	select {
	case <-timer.C:
		return nil
	case <-request.Context().Done():
		return request.Context().Err()
	}
}

func defaultRandom() float64 { return rand.Float64() }

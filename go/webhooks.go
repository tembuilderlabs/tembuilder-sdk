package tembuilder

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"strings"
	"time"
)

// DefaultWebhookTolerance is the accepted clock difference for webhook timestamps.
const DefaultWebhookTolerance = 5 * time.Minute

// WebhookEvent is a verified webhook delivery. Decode Data into
// RenderStatusEventData for "renders.status" events.
type WebhookEvent struct {
	APIVersion string          `json:"api_version"`
	Type       string          `json:"type"`
	OccurredAt *time.Time      `json:"occurred_at,omitempty"`
	Data       json.RawMessage `json:"data"`
}

// VerifyOptions tunes VerifyWebhook. Zero values use the defaults.
type VerifyOptions struct {
	// Tolerance is the accepted clock difference. Default 5 minutes.
	Tolerance time.Duration
	// Now overrides the current time, e.g. in tests.
	Now time.Time
}

// VerifyWebhook checks the Tembuilder-Signature of a webhook request and
// returns the parsed event. payload must be the raw body exactly as received.
// The signature is "v1=" + hex(HMAC-SHA256(secret, timestamp + "." + body)),
// where secret is the endpoint's unpadded base64url signing secret. Every
// failure wraps ErrWebhookVerification.
func VerifyWebhook(payload []byte, header http.Header, secret string, options VerifyOptions) (*WebhookEvent, error) {
	timestamp := header.Get("Tembuilder-Timestamp")
	signatures := strings.Join(header.Values("Tembuilder-Signature"), ",")
	if timestamp == "" || signatures == "" {
		return nil, verificationError("missing Tembuilder-Timestamp or Tembuilder-Signature header")
	}
	seconds, err := strconv.ParseInt(timestamp, 10, 64)
	if err != nil || strings.HasPrefix(timestamp, "+") || strings.HasPrefix(timestamp, "-") {
		return nil, verificationError("Tembuilder-Timestamp is not a unix timestamp")
	}
	now := options.Now
	if now.IsZero() {
		now = time.Now()
	}
	tolerance := orDefault(options.Tolerance, DefaultWebhookTolerance)
	if skew := now.Sub(time.Unix(seconds, 0)); skew > tolerance || skew < -tolerance {
		return nil, verificationError("webhook timestamp is outside the accepted tolerance")
	}
	key, err := base64.RawURLEncoding.DecodeString(strings.TrimRight(secret, "="))
	if err != nil || len(key) == 0 {
		return nil, verificationError("webhook secret is empty or not base64url")
	}

	mac := hmac.New(sha256.New, key)
	mac.Write([]byte(timestamp + "."))
	mac.Write(payload)
	expected := []byte("v1=" + hex.EncodeToString(mac.Sum(nil)))
	matched := false
	for _, candidate := range strings.Split(signatures, ",") {
		if hmac.Equal([]byte(strings.TrimSpace(candidate)), expected) {
			matched = true
		}
	}
	if !matched {
		return nil, verificationError("webhook signature does not match")
	}

	var event WebhookEvent
	if err := json.Unmarshal(payload, &event); err != nil {
		return nil, verificationError("webhook body is not a JSON object")
	}
	return &event, nil
}

func verificationError(reason string) error {
	return fmt.Errorf("%w: %s", ErrWebhookVerification, reason)
}

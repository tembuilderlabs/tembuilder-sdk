package tembuilder

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"net/http"
	"strconv"
	"testing"
	"time"
)

type webhookVector struct {
	Name      string  `json:"name"`
	Timestamp *string `json:"timestamp"`
	Signature *string `json:"signature"`
	Body      string  `json:"body"`
	Now       int64   `json:"now"`
	Valid     bool    `json:"valid"`
}

type webhookSuite struct {
	Secret           string          `json:"secret"`
	ToleranceSeconds int             `json:"tolerance_seconds"`
	Vectors          []webhookVector `json:"vectors"`
}

func vectorHeader(v webhookVector) http.Header {
	header := http.Header{}
	if v.Timestamp != nil {
		header.Set("Tembuilder-Timestamp", *v.Timestamp)
	}
	if v.Signature != nil {
		header.Set("Tembuilder-Signature", *v.Signature)
	}
	return header
}

func TestVerifyWebhookSharedVectors(t *testing.T) {
	var suite webhookSuite
	loadContract(t, "webhooks.json", &suite)
	for _, vector := range suite.Vectors {
		t.Run(vector.Name, func(t *testing.T) {
			event, err := VerifyWebhook([]byte(vector.Body), vectorHeader(vector), suite.Secret, VerifyOptions{
				Tolerance: time.Duration(suite.ToleranceSeconds) * time.Second,
				Now:       time.Unix(vector.Now, 0),
			})
			if vector.Valid {
				if err != nil {
					t.Fatal(err)
				}
				var want WebhookEvent
				_ = json.Unmarshal([]byte(vector.Body), &want)
				if event.Type != want.Type || string(event.Data) != string(want.Data) {
					t.Fatalf("event %+v", event)
				}
			} else if !errors.Is(err, ErrWebhookVerification) {
				t.Fatalf("err = %v, want ErrWebhookVerification", err)
			}
		})
	}
}

func TestVerifyWebhookDefaultsAndSecrets(t *testing.T) {
	var suite webhookSuite
	loadContract(t, "webhooks.json", &suite)
	key, _ := base64.RawURLEncoding.DecodeString(suite.Secret)
	timestamp := strconv.FormatInt(time.Now().Unix(), 10)
	body := `{"api_version":"2026-09-12","type":"webhook.test","data":{"message":"hi"}}`
	mac := hmac.New(sha256.New, key)
	mac.Write([]byte(timestamp + "." + body))
	header := http.Header{}
	header.Set("Tembuilder-Timestamp", timestamp)
	header.Add("Tembuilder-Signature", "v1=deadbeef")
	header.Add("Tembuilder-Signature", "v1="+hex.EncodeToString(mac.Sum(nil)))

	event, err := VerifyWebhook([]byte(body), header, suite.Secret+"==", VerifyOptions{})
	if err != nil || event.Type != "webhook.test" || event.OccurredAt != nil {
		t.Fatalf("event %+v err %v", event, err)
	}
	for _, secret := range []string{"", "!!!"} {
		if _, err := VerifyWebhook([]byte(body), header, secret, VerifyOptions{}); !errors.Is(err, ErrWebhookVerification) {
			t.Fatalf("secret %q: err = %v", secret, err)
		}
	}
	for _, bad := range []string{"+" + timestamp, "-5"} {
		header.Set("Tembuilder-Timestamp", bad)
		if _, err := VerifyWebhook([]byte(body), header, suite.Secret, VerifyOptions{}); !errors.Is(err, ErrWebhookVerification) {
			t.Fatalf("timestamp %q accepted", bad)
		}
	}
}

package tembuilder

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"net/http"
	"reflect"
	"testing"
	"time"
)

type contractCase struct {
	Name      string         `json:"name"`
	Operation string         `json:"operation"`
	Args      map[string]any `json:"args"`
	Request   struct {
		Method string            `json:"method"`
		Path   string            `json:"path"`
		Query  map[string]string `json:"query"`
		Body   json.RawMessage   `json:"body"`
	} `json:"request"`
	Response struct {
		Status     int               `json:"status"`
		Headers    map[string]string `json:"headers"`
		Body       json.RawMessage   `json:"body"`
		Text       *string           `json:"text"`
		BodyBase64 *string           `json:"bodyBase64"`
	} `json:"response"`
	Expect struct {
		Error *struct {
			Status int    `json:"status"`
			Code   string `json:"code"`
		} `json:"error"`
		File *struct {
			Base64      string `json:"base64"`
			Filename    string `json:"filename"`
			ContentType string `json:"content_type"`
		} `json:"file"`
	} `json:"expect"`
}

// decodeArgs maps the language-neutral args onto a typed params struct via JSON.
func decodeArgs[T any](t *testing.T, args map[string]any) T {
	t.Helper()
	var out T
	data, _ := json.Marshal(args)
	if err := json.Unmarshal(data, &out); err != nil {
		t.Fatal(err)
	}
	return out
}

func runOperation(t *testing.T, client *Client, operation string, args map[string]any) (any, error) {
	ctx := context.Background()
	switch operation {
	case "getAccount":
		return client.Account.Get(ctx)
	case "listTemplates":
		return client.Templates.List(ctx, decodeArgs[ListTemplatesParams](t, args))
	case "getTemplate":
		return client.Templates.Get(ctx, args["template_id"].(string), decodeArgs[GetTemplateParams](t, args))
	case "createRender":
		return client.Renders.Create(ctx, decodeArgs[RenderRequest](t, args["request"].(map[string]any)))
	case "listRenders":
		return client.Renders.List(ctx, decodeArgs[ListRendersParams](t, args))
	case "getRender":
		return client.Renders.Get(ctx, args["render_id"].(string))
	case "downloadRender":
		return client.Renders.Download(ctx, args["render_id"].(string))
	}
	t.Fatalf("unknown contract operation %s", operation)
	return nil, nil
}

func normalizeJSON(t *testing.T, value any) any {
	t.Helper()
	data, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	var out any
	_ = json.Unmarshal(data, &out)
	return normalizeTimes(out)
}

// normalizeTimes compares timestamps by instant (Go may render Z as +00:00).
func normalizeTimes(value any) any {
	switch typed := value.(type) {
	case map[string]any:
		for key, item := range typed {
			typed[key] = normalizeTimes(item)
		}
	case []any:
		for i, item := range typed {
			typed[i] = normalizeTimes(item)
		}
	case string:
		if parsed, err := time.Parse(time.RFC3339Nano, typed); err == nil {
			return parsed.UTC().Format(time.RFC3339Nano)
		}
	}
	return value
}

func TestSharedHTTPContract(t *testing.T) {
	var suite struct {
		APIKey string         `json:"api_key"`
		Cases  []contractCase `json:"cases"`
	}
	loadContract(t, "cases.json", &suite)
	for _, tc := range suite.Cases {
		t.Run(tc.Name, func(t *testing.T) {
			server := newStub(t, func(w http.ResponseWriter, _ *http.Request) {
				for key, value := range tc.Response.Headers {
					w.Header().Set(key, value)
				}
				w.WriteHeader(tc.Response.Status)
				switch {
				case tc.Response.BodyBase64 != nil:
					data, _ := base64.StdEncoding.DecodeString(*tc.Response.BodyBase64)
					_, _ = w.Write(data)
				case tc.Response.Text != nil:
					_, _ = w.Write([]byte(*tc.Response.Text))
				default:
					_, _ = w.Write(tc.Response.Body)
				}
			})
			client := newTestClient(t, server, WithAPIKey(suite.APIKey))
			value, err := runOperation(t, client, tc.Operation, tc.Args)

			if server.count() != 1 {
				t.Fatalf("sent %d requests", server.count())
			}
			sent := server.requests[0]
			if sent.Method != tc.Request.Method || sent.Path != tc.Request.Path {
				t.Fatalf("sent %s %s", sent.Method, sent.Path)
			}
			if !reflect.DeepEqual(normalizeTimes(toAny(sent.Query)), normalizeTimes(toAny(tc.Request.Query))) {
				t.Fatalf("query %v, want %v", sent.Query, tc.Request.Query)
			}
			if sent.Header.Get("ApiKey") != suite.APIKey {
				t.Fatalf("ApiKey header %q", sent.Header.Get("ApiKey"))
			}
			if string(tc.Request.Body) == "null" {
				if len(sent.Body) != 0 {
					t.Fatalf("unexpected body %s", sent.Body)
				}
			} else {
				var got, want any
				_ = json.Unmarshal(sent.Body, &got)
				_ = json.Unmarshal(tc.Request.Body, &want)
				if !reflect.DeepEqual(got, want) {
					t.Fatalf("body %s, want %s", sent.Body, tc.Request.Body)
				}
			}

			switch {
			case tc.Expect.Error != nil:
				var apiErr *APIError
				if !errors.As(err, &apiErr) || apiErr.StatusCode != tc.Expect.Error.Status || apiErr.Code != tc.Expect.Error.Code {
					t.Fatalf("error %v, want %+v", err, tc.Expect.Error)
				}
			case tc.Expect.File != nil:
				file := value.(*RenderFile)
				if err != nil || base64.StdEncoding.EncodeToString(file.Content) != tc.Expect.File.Base64 ||
					file.Filename != tc.Expect.File.Filename || file.ContentType != tc.Expect.File.ContentType {
					t.Fatalf("file %+v err %v", file, err)
				}
			default:
				if err != nil {
					t.Fatal(err)
				}
				var want any
				_ = json.Unmarshal(tc.Response.Body, &want)
				if got := normalizeJSON(t, value); !reflect.DeepEqual(got, normalizeTimes(want)) {
					t.Fatalf("result %v\nwant   %v", got, want)
				}
			}
		})
	}
}

func toAny(m map[string]string) any {
	out := map[string]any{}
	for key, value := range m {
		out[key] = value
	}
	return out
}

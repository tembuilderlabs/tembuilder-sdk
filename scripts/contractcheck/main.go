// Command contractcheck verifies that contract/cases.json, the HTTP cases
// every SDK replays, agrees with the public OpenAPI contract:
//
//   - every operation in the spec has at least one case, and every case names
//     an operation of the spec;
//   - each case sends its operation's method and path;
//   - each successful case sends a request the spec accepts;
//   - each response is one the spec documents (status, content type and body
//     schema), unless the case says why it is deliberately "off_contract".
//
// Because each SDK's contract test fails on an operation it cannot call, a new
// operation in the spec cannot ship until all three SDKs wrap it.
//
// Usage: go run . <openapi.yaml> <cases.json>
package main

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"sort"
	"strings"

	"github.com/getkin/kin-openapi/openapi3"
	"github.com/getkin/kin-openapi/openapi3filter"
	"github.com/getkin/kin-openapi/routers"
	"github.com/getkin/kin-openapi/routers/legacy"
)

type contractCase struct {
	Name        string `json:"name"`
	Operation   string `json:"operation"`
	OffContract string `json:"off_contract"`
	Request     struct {
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
}

type suite struct {
	APIKey string         `json:"api_key"`
	Cases  []contractCase `json:"cases"`
}

func init() {
	openapi3filter.RegisterBodyDecoder("application/pdf", openapi3filter.FileBodyDecoder)
}

func main() {
	if len(os.Args) != 3 {
		fmt.Fprintln(os.Stderr, "usage: contractcheck <openapi.yaml> <cases.json>")
		os.Exit(2)
	}
	problems, err := checkFiles(os.Args[1], os.Args[2])
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	if len(problems) > 0 {
		fmt.Fprintf(os.Stderr, "contract/cases.json disagrees with the spec:\n  - %s\n", strings.Join(problems, "\n  - "))
		os.Exit(1)
	}
	fmt.Println("contract cases agree with the spec")
}

func checkFiles(specPath, casesPath string) ([]string, error) {
	doc, err := openapi3.NewLoader().LoadFromFile(specPath)
	if err != nil {
		return nil, fmt.Errorf("load %s: %w", specPath, err)
	}
	if err := doc.Validate(context.Background()); err != nil {
		return nil, fmt.Errorf("invalid %s: %w", specPath, err)
	}
	raw, err := os.ReadFile(casesPath)
	if err != nil {
		return nil, err
	}
	var s suite
	if err := json.Unmarshal(raw, &s); err != nil {
		return nil, fmt.Errorf("parse %s: %w", casesPath, err)
	}
	return check(doc, s)
}

func check(doc *openapi3.T, s suite) ([]string, error) {
	router, err := legacy.NewRouter(doc)
	if err != nil {
		return nil, err
	}
	var problems []string
	covered := map[string]bool{}
	for _, c := range s.Cases {
		covered[c.Operation] = true
		problems = append(problems, checkCase(router, s.APIKey, c)...)
	}
	var operations []string
	for _, item := range doc.Paths.Map() {
		for _, op := range item.Operations() {
			operations = append(operations, op.OperationID)
		}
	}
	sort.Strings(operations)
	for _, id := range operations {
		if !covered[id] {
			problems = append(problems, "operation "+id+" has no contract case")
		}
	}
	return problems, nil
}

func checkCase(router routers.Router, apiKey string, c contractCase) []string {
	fail := func(format string, args ...any) []string {
		return []string{fmt.Sprintf("%q: ", c.Name) + fmt.Sprintf(format, args...)}
	}
	target := url.URL{Scheme: "https", Host: "api.tembuilder.com", Path: c.Request.Path}
	query := url.Values{}
	for name, value := range c.Request.Query {
		query.Set(name, value)
	}
	target.RawQuery = query.Encode()
	var body []byte
	if len(c.Request.Body) > 0 && string(c.Request.Body) != "null" {
		body = c.Request.Body
	}
	req, err := http.NewRequest(c.Request.Method, target.String(), bytes.NewReader(body))
	if err != nil {
		return fail("invalid request: %v", err)
	}
	req.Header.Set("ApiKey", apiKey)
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}

	route, pathParams, err := router.FindRoute(req)
	if err != nil {
		return fail("%s %s is not an operation of the spec", c.Request.Method, c.Request.Path)
	}
	if route.Operation.OperationID != c.Operation {
		return fail("sends %s %s, which is %s, not %s", c.Request.Method, c.Request.Path, route.Operation.OperationID, c.Operation)
	}
	input := &openapi3filter.RequestValidationInput{
		Request: req, PathParams: pathParams, Route: route,
		Options: &openapi3filter.Options{AuthenticationFunc: openapi3filter.NoopAuthenticationFunc, MultiError: true},
	}
	// Error cases may send what the API rejects; successful ones must not.
	if c.Response.Status < 300 {
		if err := openapi3filter.ValidateRequest(context.Background(), input); err != nil {
			return fail("request violates the spec: %v", err)
		}
	}
	if c.OffContract != "" {
		return nil
	}

	var responseBody []byte
	switch {
	case c.Response.BodyBase64 != nil:
		if responseBody, err = base64.StdEncoding.DecodeString(*c.Response.BodyBase64); err != nil {
			return fail("invalid bodyBase64: %v", err)
		}
	case c.Response.Text != nil:
		responseBody = []byte(*c.Response.Text)
	default:
		responseBody = c.Response.Body
	}
	header := http.Header{}
	for name, value := range c.Response.Headers {
		header.Set(name, value)
	}
	err = openapi3filter.ValidateResponse(context.Background(), &openapi3filter.ResponseValidationInput{
		RequestValidationInput: input,
		Status:                 c.Response.Status,
		Header:                 header,
		Body:                   io.NopCloser(bytes.NewReader(responseBody)),
		Options:                &openapi3filter.Options{IncludeResponseStatus: true, MultiError: true},
	})
	if err != nil {
		return fail("response %d violates the spec (mark the case off_contract only if that is deliberate): %v", c.Response.Status, err)
	}
	return nil
}

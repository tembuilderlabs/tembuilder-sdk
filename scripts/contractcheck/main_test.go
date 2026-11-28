package main

import (
	"bytes"
	"encoding/json"
	"os"
	"strings"
	"testing"

	"github.com/getkin/kin-openapi/openapi3"
)

const (
	specPath  = "../../openapi/tembuilder.yaml"
	casesPath = "../../contract/cases.json"
)

func load(t *testing.T) (*openapi3.T, suite) {
	t.Helper()
	doc, err := openapi3.NewLoader().LoadFromFile(specPath)
	if err != nil {
		t.Fatal(err)
	}
	raw, err := os.ReadFile(casesPath)
	if err != nil {
		t.Fatal(err)
	}
	var s suite
	if err := json.Unmarshal(raw, &s); err != nil {
		t.Fatal(err)
	}
	return doc, s
}

func caseNamed(t *testing.T, s suite, name string) int {
	t.Helper()
	for i, c := range s.Cases {
		if c.Name == name {
			return i
		}
	}
	t.Fatalf("no case %q", name)
	return -1
}

func expectProblem(t *testing.T, doc *openapi3.T, s suite, want string) {
	t.Helper()
	problems, err := check(doc, s)
	if err != nil {
		t.Fatal(err)
	}
	for _, p := range problems {
		if strings.Contains(p, want) {
			return
		}
	}
	t.Fatalf("expected a problem containing %q, got %v", want, problems)
}

func TestRepositoryCasesAgreeWithTheSpec(t *testing.T) {
	problems, err := checkFiles(specPath, casesPath)
	if err != nil {
		t.Fatal(err)
	}
	if len(problems) > 0 {
		t.Fatalf("problems: %v", problems)
	}
}

func TestDetectsAnOperationWithoutCases(t *testing.T) {
	doc, s := load(t)
	var kept []contractCase
	for _, c := range s.Cases {
		if c.Operation != "listRenders" {
			kept = append(kept, c)
		}
	}
	s.Cases = kept
	expectProblem(t, doc, s, "operation listRenders has no contract case")
}

func TestDetectsADocumentedResponseWithoutCases(t *testing.T) {
	doc, s := load(t)
	var kept []contractCase
	for _, c := range s.Cases {
		if !(c.Operation == "createRender" && c.Response.Status == 503) {
			kept = append(kept, c)
		}
	}
	s.Cases = kept
	expectProblem(t, doc, s, "operation createRender documents response 503 but no case covers it")
}

func TestDetectsACaseForAnUnknownRoute(t *testing.T) {
	doc, s := load(t)
	s.Cases[0].Request.Path = "/v1/whoami"
	expectProblem(t, doc, s, "GET /v1/whoami is not an operation of the spec")
}

func TestDetectsACaseCallingTheWrongOperation(t *testing.T) {
	doc, s := load(t)
	s.Cases[0].Operation = "listTemplates"
	expectProblem(t, doc, s, "which is getAccount, not listTemplates")
}

func TestDetectsAnInvalidSuccessfulRequest(t *testing.T) {
	doc, s := load(t)
	for i, c := range s.Cases {
		if c.Operation == "createRender" && c.Response.Status == 202 {
			s.Cases[i].Request.Body = json.RawMessage(`{"parameters":{}}`) // template_id is required
			expectProblem(t, doc, s, "request violates the spec")
			return
		}
	}
	t.Fatal("no accepted createRender case")
}

func TestDetectsAResponseOutsideTheSpec(t *testing.T) {
	doc, s := load(t)
	s.Cases[0].Response.Body = json.RawMessage(`{"api_key_id":42}`)
	expectProblem(t, doc, s, "response 200 violates the spec")

	doc, s = load(t)
	s.Cases[0].Response.Status = 418
	expectProblem(t, doc, s, "response 418 violates the spec")
}

func TestOffContractCasesSkipOnlyResponseValidation(t *testing.T) {
	doc, s := load(t)
	i := caseNamed(t, s, "getRender maps a gateway error without a JSON body")
	s.Cases[i].OffContract = ""
	expectProblem(t, doc, s, "response 500 violates the spec")

	doc, s = load(t)
	s.Cases[i].Request.Path = "/v1/nope"
	expectProblem(t, doc, s, "GET /v1/nope is not an operation of the spec")
}

func TestBinaryAndTextBodies(t *testing.T) {
	doc, s := load(t)
	for i, c := range s.Cases {
		if c.Response.BodyBase64 != nil {
			bad := "%%%"
			s.Cases[i].Response.BodyBase64 = &bad
			expectProblem(t, doc, s, "invalid bodyBase64")
			return
		}
	}
	t.Fatal("no binary case")
}

func TestReportsUnreadableInputs(t *testing.T) {
	if _, err := checkFiles("missing.yaml", casesPath); err == nil {
		t.Fatal("missing spec accepted")
	}
	if _, err := checkFiles(specPath, "missing.json"); err == nil {
		t.Fatal("missing cases accepted")
	}
	dir := t.TempDir()
	bad := dir + "/cases.json"
	if err := os.WriteFile(bad, []byte("{"), 0o600); err != nil {
		t.Fatal(err)
	}
	if _, err := checkFiles(specPath, bad); err == nil {
		t.Fatal("invalid cases accepted")
	}
	invalidSpec := dir + "/spec.yaml"
	if err := os.WriteFile(invalidSpec, []byte("openapi: 3.0.3\ninfo: {title: x, version: '1'}\npaths:\n  /v1/me:\n    get:\n      responses: {}\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	if _, err := checkFiles(invalidSpec, casesPath); err == nil {
		t.Fatal("invalid spec accepted")
	}
}

func TestRunReportsEveryOutcome(t *testing.T) {
	dir := t.TempDir()
	broken := dir + "/cases.json"
	data, err := os.ReadFile(casesPath)
	if err != nil {
		t.Fatal(err)
	}
	var s suite
	if err := json.Unmarshal(data, &s); err != nil {
		t.Fatal(err)
	}
	s.Cases = s.Cases[1:] // drops getAccount's only 200 case
	encoded, err := json.Marshal(s)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(broken, encoded, 0o600); err != nil {
		t.Fatal(err)
	}
	for name, tc := range map[string]struct {
		args   []string
		code   int
		stdout string
		stderr string
	}{
		"usage":           {[]string{specPath}, 2, "", "usage: contractcheck"},
		"unreadable":      {[]string{specPath, dir + "/missing.json"}, 1, "", "missing.json"},
		"disagreement":    {[]string{specPath, broken}, 1, "", "operation getAccount documents response 200 but no case covers it"},
		"agree with spec": {[]string{specPath, casesPath}, 0, "contract cases agree with the spec", ""},
	} {
		var stdout, stderr bytes.Buffer
		if code := run(tc.args, &stdout, &stderr); code != tc.code {
			t.Fatalf("%s: exit %d, want %d (%s)", name, code, tc.code, stderr.String())
		}
		if !strings.Contains(stdout.String(), tc.stdout) || !strings.Contains(stderr.String(), tc.stderr) {
			t.Fatalf("%s: stdout %q stderr %q", name, stdout.String(), stderr.String())
		}
	}
}

func TestReportsAnInvalidSpec(t *testing.T) {
	doc, s := load(t)
	doc.Paths.Find("/v1/me").Get.Responses = openapi3.NewResponses() // an operation must document a response
	if _, err := check(doc, s); err == nil {
		t.Fatal("an invalid spec was routed")
	}
}

func TestReportsAnUnbuildableRequest(t *testing.T) {
	doc, s := load(t)
	s.Cases[0].Request.Method = "NOT A METHOD"
	expectProblem(t, doc, s, "invalid request")
}

func TestMainExitsWithTheRunResult(t *testing.T) {
	args, previous := os.Args, exit
	t.Cleanup(func() { os.Args, exit = args, previous })
	code := -1
	exit = func(c int) { code = c }
	os.Args = []string{"contractcheck"}
	main()
	if code != 2 {
		t.Fatalf("exit %d, want 2 for missing arguments", code)
	}
}

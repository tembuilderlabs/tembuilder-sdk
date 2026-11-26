---
name: tembuilder-sdk-public-api
description: Sync the public API contract from tembuilder-be into the SDKs, regenerate the Node/Python/Go clients, wrap new operations and prove everything still works. Use after any change to tembuilder-be's internal/publicapi/openapi.yaml, when CI says the spec copy is stale, or on a sync-spec PR.
---

# Public API (SDK half)

Requires the BE half (`tembuilder-be/.agents/skills/public-api`) first: the
contract `tembuilder-be/svr/service-svr/internal/publicapi/openapi.yaml` is the
source of truth and `openapi/tembuilder.yaml` here is a byte-for-byte copy.
Never edit the copy or the generated directories (`node/src/generated`,
`python/src/tembuilder/_generated`, `go/internal/api`).

## Steps

1. Copy the contract and regenerate all three SDKs (sibling checkout of
   tembuilder-be expected; otherwise pass `BE_SPEC=<path>`):
   ```bash
   make sync-spec
   ```
2. If an operation was **added**, wire it everywhere — the checks below fail
   until it is:
   - a case per documented outcome in `contract/cases.json` (success and the
     main errors; `operation` = the `operationId`);
   - a wrapper method in `node/src/client.ts`, `python/src/tembuilder/_client.py`
     (sync **and** async resources) and the Go client (`go/*.go`), plus each
     SDK's contract dispatcher (`node/test/contract.test.ts`,
     `python/tests/test_contract.py`, `go/contract_test.go`);
   - tests keeping hand-written code at 100% coverage;
   - the live flow in `e2e/{node,python,go}` when it is something a customer
     would call in the quickstart.
   A changed field usually needs nothing beyond regeneration: type errors in
   the wrappers point at what to adapt.
3. Verify:
   ```bash
   make all                 # check-spec, lint, drift, tests (100%), conformance, builds, e2e
   make breaking            # against origin/main; a break needs a major release
   make e2e-live            # with BE `make dev` + WA `pnpm dev` running, renders real PDFs
   ```
   `make conformance` runs `scripts/contractcheck`: every operation has a case,
   each case's request/response is documented, unless it states why it is
   `off_contract`.
4. Commit with the Conventional Commit type users will see in the changelog:
   `feat` (new operation/field), `fix`, `docs`/`chore` (no SDK-visible change),
   `feat!` + label `breaking-change` for a major. On GitHub the `sync-spec`
   workflow opens this PR automatically (title defaults to `feat(api)`; adjust
   it before merging). Merging feeds release-please; releases publish and then
   verify the published packages on staging.
5. Hand off to `tembuilder-wa/.agents/skills/public-api` for the API reference
   docs.

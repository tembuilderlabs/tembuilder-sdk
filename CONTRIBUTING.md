# Contributing

## Changing the API surface

The contract is owned by the backend:
`tembuilder-be/svr/service-svr/internal/publicapi/openapi.yaml`. The backend
mounts exactly its operations and validates every handler response against
it, so it always describes what is deployed. `openapi/tembuilder.yaml` here is
a byte-for-byte copy: never edit it (`make check-spec` and CI reject that).

1. Change the backend and its contract together (see the backend's
   `public-api` skill); once merged, the `sync-spec` workflow opens a PR here.
   Locally, with both repositories side by side: `make sync-spec` (copies the
   contract and runs `make generate`).
2. Every operation needs a case in `contract/cases.json` and a wrapper in
   **every** SDK's hand-written layer. `make conformance` fails on an operation
   without a case, on cases that disagree with the spec, and each SDK's
   contract test fails on an operation it cannot call.
3. `make all` — spec sync, lint, drift, tests (100% coverage), conformance,
   builds, fresh-app e2e. With a local stack running: `make e2e-live`.
4. Commit with a Conventional Commit message, scoped by package when it
   only concerns one (`feat(python): …`). The spec affects all three.

Never edit `node/src/generated`, `python/src/tembuilder/_generated` or
`go/internal/api`. CI regenerates them and fails on any difference.

## Breaking changes

`scripts/check-breaking.sh` compares the spec with the base branch using
oasdiff (the backend runs the same check against its last release before
deploying). A breaking change (removed field, new required input, narrowed
enum, …) fails CI. If it is intended, label the PR `breaking-change` and use
a `feat!:` commit so release-please bumps the major version of every SDK.

## Local setup

Requirements: Node 22 + pnpm 9, Python ≥ 3.11 + uv, Go ≥ 1.24.

```bash
make install
make all
```

`make conformance` starts a Prism mock of the spec (port 4010).

## End-to-end: the packages as users get them

`e2e/` holds one tiny consumer app per language. `e2e/run.sh` creates a fresh
project outside the repository, installs the SDK into it and runs the app:

```bash
make e2e                                   # packages built from this checkout
make e2e-live                              # same, rendering against .env.smoke
make e2e-published                         # latest from npm, PyPI and the Go proxy
make e2e-published NODE_VERSION=0.2.0      # an exact released version
./e2e/run.sh python 0.2.0                  # one SDK
```

Each app checks the installed version, the exports and the shared webhook
vectors. With `TEMBUILDER_API_KEY`, `TEMBUILDER_BASE_URL`,
`TEMBUILDER_SMOKE_TEMPLATE` and `TEMBUILDER_PARAMETER_TEMPLATE` set it also
renders real PDFs: account, template input, list, render, wait, download
through the signed `file_url` and through the API, render log, 404/401 errors,
and the parameter scenarios of `contract/parameters.json` (every parameter
type, defaults only, a wrongly typed parameter that must fail).
`REQUIRE_LIVE=1` makes a missing live environment fail. For a local stack,
keep those variables in the git-ignored `.env.smoke` and run `make e2e-live`.

`TEMBUILDER_PARAMETER_TEMPLATE` is the slug of `e2e/parameter-template`
imported into the smoke project (Templates → Import, then publish):
`./e2e/build-parameter-template.sh` packs it into that ZIP. On GitHub it is
the `SMOKE_PARAMETER_TEMPLATE` variable of the `production` environment.

## Pinned generators

| SDK | Generator | Pinned in |
| --- | --- | --- |
| Node | openapi-typescript 7.13.0 (types) + openapi-fetch 0.17.0 (runtime) | `node/package.json` |
| Python | openapi-python-client 0.29.1 (0.30 switched to the `httpx2` fork) | `scripts/generate.sh` |
| Go | oapi-codegen v2.7.0 + runtime v1.8.0 (keeps Go ≥ 1.24 support) | `scripts/generate.sh`, `go/go.mod` |

Upgrade a generator in its own PR; the drift and contract suites show exactly
what changed.

## Releasing

Merging to `main` lets release-please open one release PR covering every changed package (each still gets its own version, tag and changelog).
Merging that PR tags `node/vX`, `python/vX` or `go/vX` and the release
workflow publishes from CI (npm with provenance, PyPI via trusted
publishing). Nothing is published from a laptop.

Each release runs `e2e/run.sh <sdk> local` before publishing, then installs
the exact released version from its registry into a fresh app and renders a
real PDF on production (`verify` job, `production` environment, a key scoped
to a test project). The production smoke workflow does the same with the
latest published versions after every production deploy of a backend service
or the renderer; run it by hand after infrastructure changes no deploy carries.

## Spec sync setup

CI reads the private backend, the sync PR must trigger CI, and production
deploys of `tembuilder-be` services and the `tembuilder-wa` renderer start the
production smoke test here (`repository_dispatch: production-deployed`). All of
it uses one GitHub App of the tembuilderlabs organisation (`spec-sync`),
installed on `tembuilder-be`, `tembuilder-wa` and `tembuilder-sdk` with
*Contents: read & write* and *Pull requests: read & write*. All three
repositories need the variable `SPEC_SYNC_APP_ID` and the secret
`SPEC_SYNC_APP_PRIVATE_KEY`. Until they exist, those steps are skipped.

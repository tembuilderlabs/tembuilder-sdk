# Tembuilder SDKs

Official clients for the [Tembuilder](https://tembuilder.com) PDF rendering API.

| Language | Package | Install |
| --- | --- | --- |
| Node.js / TypeScript | [`@tembuilderlabs/sdk`](node/) | `npm install @tembuilderlabs/sdk` |
| Python | [`tembuilder`](python/) | `pip install tembuilder` |
| Go | [`github.com/tembuilderlabs/tembuilder-sdk/go`](go/) | `go get github.com/tembuilderlabs/tembuilder-sdk/go` |

Every SDK covers the same API:

| Resource | Operations |
| --- | --- |
| Account | `GET /v1/me` |
| Templates | list (paginated), get (versions, variants, parameter JSON Schema, example input) |
| Renders | create, get status, list (paginated), download PDF, create-and-wait |
| Webhooks | verify `Tembuilder-Signature` |

Plus the same behaviour: bounded retries of transient failures (never resending
a render request that might have been accepted), typed errors with the API's
stable `code`, polling that tolerates the brief 404 right after a render is
queued, and pagination helpers.

API reference: <https://tembuilder.com/docs/developers/render-reference/>

## How this repository is built

```
tembuilder-be …/publicapi/openapi.yaml  ← source of truth (the backend mounts and tests it)
        │  make sync-spec (byte-for-byte copy, CI-checked)
openapi/tembuilder.yaml   ← the public API contract
        │  scripts/generate.sh (pinned generators)
        ├── node/src/generated          openapi-typescript   + openapi-fetch
        ├── python/src/tembuilder/_generated  openapi-python-client (httpx + attrs)
        └── go/internal/api             oapi-codegen
contract/                 ← language-neutral HTTP cases and webhook vectors,
                            replayed by every SDK's test suite
```

Generated directories are never edited by hand. Each SDK adds a small
hand-written layer (configuration, retries, errors, polling, pagination,
webhooks) that is covered 100% by tests.

Guard rails (all enforced in CI, see [CONTRIBUTING.md](CONTRIBUTING.md)):

1. Backend contract — the deployed API mounts exactly the spec's operations and its tests validate every response; this copy must equal it.
2. Spec lint (Redocly) — every operation has an ID, description, tag and error responses.
3. Breaking-change check (oasdiff) — a breaking change needs an explicit major release.
4. Drift check — regenerating from the spec must produce the committed code.
5. 100% coverage of hand-written code in all three languages.
6. Shared contract suite — every operation has cases that agree with the spec, and the three SDKs must send and parse the same HTTP.
7. Conformance — the Node SDK runs against a Prism mock that rejects any request violating the spec.
8. Production smoke test after every backend or renderer deploy, and nightly — the deployed API still matches the published SDKs.
9. Releases only from CI tags (release-please), npm provenance and PyPI trusted publishing.

## License

MIT

# Tembuilder SDK instructions

Official Node, Python and Go SDKs generated from the public API contract.
The contract is owned by tembuilder-be
(`svr/service-svr/internal/publicapi/openapi.yaml`); `openapi/tembuilder.yaml`
is a byte-for-byte copy. See README.md and CONTRIBUTING.md.

`.agents/skills/` is the source of truth. `.claude/skills` and
`.codex/skills` are symlink adapters; do not edit them directly.

Before starting a matching workflow, load the relevant local skill:

- `public-api` for any API change: syncing the contract, regenerating,
  wrapping new operations, verifying and releasing.

`make all` must pass before any change is done; with a local stack running,
also `make e2e-live`.

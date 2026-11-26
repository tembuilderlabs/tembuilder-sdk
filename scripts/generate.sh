#!/usr/bin/env bash
# Regenerates every SDK's low-level layer from openapi/tembuilder.yaml.
# Generated directories are fully replaced; never edit them by hand.
# Generator versions are pinned here and in each package manifest so output is
# reproducible (CI runs this script and fails on any diff).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SPEC="$ROOT/openapi/tembuilder.yaml"
OPENAPI_PYTHON_CLIENT_VERSION="0.29.1"
OAPI_CODEGEN_VERSION="v2.7.0"

echo "==> node (openapi-typescript)"
(cd "$ROOT/node" && pnpm exec openapi-typescript "$SPEC" --output src/generated/schema.ts)

echo "==> python (openapi-python-client $OPENAPI_PYTHON_CLIENT_VERSION)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
uv tool run --from "openapi-python-client==$OPENAPI_PYTHON_CLIENT_VERSION" openapi-python-client generate \
  --path "$SPEC" \
  --config "$ROOT/python/openapi-python-client.yml" \
  --meta none \
  --output-path "$tmp/_generated" >/dev/null
rm -rf "$ROOT/python/src/tembuilder/_generated"
cp -R "$tmp/_generated" "$ROOT/python/src/tembuilder/_generated"
(cd "$ROOT/python" && uv run --frozen ruff format --quiet src/tembuilder/_generated && uv run --frozen ruff check --quiet --fix --select I,F401 src/tembuilder/_generated || true)

echo "==> go (oapi-codegen $OAPI_CODEGEN_VERSION)"
(cd "$ROOT/go" && go run "github.com/oapi-codegen/oapi-codegen/v2/cmd/oapi-codegen@$OAPI_CODEGEN_VERSION" -config oapi-codegen.yaml "$SPEC")

echo "done"

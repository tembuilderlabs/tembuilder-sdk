#!/usr/bin/env bash
# Packs e2e/parameter-template into a ZIP the Tembuilder app imports
# (Templates → Import). The live e2e renders it with every parameter type.
set -euo pipefail
root="$(cd "$(dirname "$0")" && pwd)/parameter-template"
out="${1:-sdk-parameter-coverage.zip}"
out="$(cd "$(dirname "$out")" && pwd)/$(basename "$out")"
rm -f "$out"
(cd "$root" && zip -qrXD "$out" manifest.json v1)
echo "$out"

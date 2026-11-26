#!/usr/bin/env bash
# Detects breaking changes in openapi/tembuilder.yaml against a base ref.
# A breaking change fails unless the PR is explicitly a major release
# (ALLOW_BREAKING=1, set by CI when the PR carries the "breaking-change" label).
set -euo pipefail
BASE="${1:-origin/main}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SPEC="openapi/tembuilder.yaml"
OASDIFF_VERSION="v1.39.0"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
if ! git -C "$ROOT" show "$BASE:$SPEC" > "$tmp/base.yaml" 2>/dev/null; then
  echo "No $SPEC on $BASE; nothing to compare."
  exit 0
fi

set +e
go run "github.com/oasdiff/oasdiff@$OASDIFF_VERSION" breaking "$tmp/base.yaml" "$ROOT/$SPEC" --fail-on ERR
status=$?
set -e
if [ "$status" -ne 0 ]; then
  if [ "${ALLOW_BREAKING:-0}" = "1" ]; then
    echo "Breaking changes allowed for this major release."
    exit 0
  fi
  echo "Breaking API change detected. Keep the change backward compatible, or label the PR 'breaking-change' to release a new major version."
  exit 1
fi
echo "No breaking changes."

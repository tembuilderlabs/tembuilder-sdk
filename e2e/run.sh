#!/usr/bin/env bash
# Installs an SDK into a brand-new consumer app outside the repository and runs
# it, exactly as a user would:
#
#   e2e/run.sh <node|python|go|all> local      # the package built from this checkout
#   e2e/run.sh <node|python|go> <X.Y.Z>        # that version from npm / PyPI / the Go proxy
#   e2e/run.sh <node|python|go|all> latest     # the newest published version
#
# Offline checks always run. With TEMBUILDER_API_KEY, TEMBUILDER_BASE_URL and
# TEMBUILDER_SMOKE_TEMPLATE set, each app also renders a real PDF; REQUIRE_LIVE=1
# turns a missing live environment into a failure.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
language="${1:?usage: e2e/run.sh <node|python|go|all> <local|latest|X.Y.Z>}"
source="${2:?usage: e2e/run.sh <node|python|go|all> <local|latest|X.Y.Z>}"
export WEBHOOK_VECTORS="$root/contract/webhooks.json"

if [ "$language" = all ]; then
  for each in node python go; do "$0" "$each" "$source"; done
  exit 0
fi

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

# A just-published version can take several minutes to become installable
# (npm took over five once): wait up to 15 minutes.
retry() {
  local attempt
  for attempt in $(seq 1 30); do
    "$@" && return 0
    [ "$source" = local ] && return 1
    echo "not available yet (attempt $attempt); retrying in 30s" >&2
    sleep 30
  done
  return 1
}

local_version() {
  sed -nE "s/.*['\"]([0-9]+\.[0-9]+\.[0-9]+[^'\"]*)['\"].*x-release-please-version.*/\1/p" "$1"
}

echo "==> $language SDK ($source) in a fresh app: $work"
case "$language" in
  node)
    cp "$root/e2e/node/app.mjs" "$work/"
    printf '{ "name": "tembuilder-e2e", "private": true, "type": "module" }\n' > "$work/package.json"
    if [ "$source" = local ]; then
      (cd "$root/node" && pnpm build >/dev/null && npm pack --silent --pack-destination "$work" >/dev/null)
      package="$(ls "$work"/tembuilderlabs-sdk-*.tgz)"
      export EXPECTED_VERSION="$(local_version "$root/node/src/version.ts")"
    else
      package="@tembuilderlabs/sdk@$source"
      [ "$source" = latest ] || export EXPECTED_VERSION="$source"
    fi
    (cd "$work" && retry npm install --no-audit --no-fund --silent "$package")
    (cd "$work" && node app.mjs)
    ;;
  python)
    cp "$root/e2e/python/app.py" "$work/"
    uv venv --quiet --python ">=3.11" "$work/venv"
    if [ "$source" = local ]; then
      (cd "$root/python" && uv build --quiet --wheel --out-dir "$work/dist")
      package="$(ls "$work"/dist/tembuilder-*.whl)"
      export EXPECTED_VERSION="$(local_version "$root/python/src/tembuilder/_version.py")"
    elif [ "$source" = latest ]; then
      package="tembuilder"
    else
      package="tembuilder==$source"
      export EXPECTED_VERSION="$source"
    fi
    retry uv pip install --quiet --refresh --python "$work/venv/bin/python" "$package"
    (cd "$work" && venv/bin/python app.py)
    ;;
  go)
    cp "$root/e2e/go/main.go" "$work/"
    module=github.com/tembuilderlabs/tembuilder-sdk/go
    (cd "$work" && go mod init example.com/tembuilder-e2e >/dev/null 2>&1)
    if [ "$source" = local ]; then
      (cd "$work" && go mod edit -require "$module@v0.0.0" -replace "$module=$root/go")
      export EXPECTED_VERSION="$(local_version "$root/go/version.go")"
    else
      version="$source"
      [ "$source" = latest ] || { version="v$source"; export EXPECTED_VERSION="$source"; }
      (cd "$work" && GOPROXY=https://proxy.golang.org,direct retry go get "$module@$version")
    fi
    (cd "$work" && go mod tidy >/dev/null 2>&1 && go run .)
    ;;
  *)
    echo "unknown language: $language" >&2
    exit 2
    ;;
esac

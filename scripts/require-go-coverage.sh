#!/usr/bin/env bash
# Fails unless the hand-written Go package is 100% covered. internal/api is
# generated and verified by the drift check and the shared contract suite.
set -euo pipefail
total="$(go tool cover -func="$1" | awk '/^total:/ {print $3}')"
if [ "$total" != "100.0%" ]; then
  go tool cover -func="$1" | grep -v '100.0%'
  echo "Go coverage is $total; 100.0% is required."
  exit 1
fi
echo "Go coverage: $total"

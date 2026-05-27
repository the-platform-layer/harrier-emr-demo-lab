#!/usr/bin/env bash
set -euo pipefail

scenario="${1:-}"
if [[ -z "$scenario" ]]; then
  echo "usage: $0 <scenario>" >&2
  exit 2
fi

echo "TODO: run demo scenario: $scenario"


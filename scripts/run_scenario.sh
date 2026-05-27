#!/usr/bin/env bash
set -euo pipefail

scenario="${1:-}"
if [[ -z "$scenario" ]]; then
  echo "usage: $0 <scenario>" >&2
  exit 2
fi

repo_root="$(cd "$(dirname "$0")/.." && pwd)"

case "$scenario" in
  happy_path)
    SCENARIO="$scenario" "$repo_root/scripts/submit_step.sh"
    ;;
  *)
    echo "scenario is not implemented yet: $scenario" >&2
    exit 2
    ;;
esac

#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
scenario="${1:-}"
context_file="${CONTEXT_FILE:-$repo_root/.harrier-demo/last-context.json}"

if [[ -n "$scenario" ]]; then
  latest_context="$(find "$repo_root/.harrier-demo/runs" -maxdepth 1 -name "$scenario-*.json" -type f 2>/dev/null | sort | tail -n 1 || true)"
  if [[ -n "$latest_context" ]]; then
    context_file="$latest_context"
  fi
fi

if [[ ! -f "$context_file" ]]; then
  echo "Context file not found: $context_file" >&2
  echo "Run a scenario first or pass CONTEXT_FILE=/path/to/context.json." >&2
  exit 2
fi

context_value() {
  python3 - "$context_file" "$1" <<'PY'
import json
import sys

path, name = sys.argv[1:]
with open(path, encoding="utf-8") as handle:
    data = json.load(handle)
value = data.get(name, "")
if value is None:
    value = ""
print(value)
PY
}

context_scenario="$(context_value scenario)"
if [[ -n "$scenario" && "$context_scenario" != "$scenario" ]]; then
  echo "Context scenario $context_scenario does not match requested scenario $scenario" >&2
  exit 2
fi

region="$(context_value region)"
cluster_id="$(context_value cluster_id)"
step_id="$(context_value step_id)"
input_path="$(context_value input_path)"
output_path="$(context_value output_path)"
job_uri="$(context_value job_uri)"

is_s3_uri_with_key() {
  local uri="$1"
  [[ "$uri" == s3://* ]] || return 1
  local without_scheme="${uri#s3://}"
  local key="${without_scheme#*/}"
  [[ "$key" != "$without_scheme" && -n "$key" ]]
}

remove_s3_object() {
  local uri="$1"
  if ! is_s3_uri_with_key "$uri"; then
    return
  fi
  if ! command -v aws >/dev/null 2>&1; then
    echo "aws CLI not found; skipping $uri"
    return
  fi
  aws s3 rm "$uri" --region "$region" || true
}

remove_s3_prefix() {
  local uri="$1"
  if ! is_s3_uri_with_key "$uri"; then
    return
  fi
  if ! command -v aws >/dev/null 2>&1; then
    echo "aws CLI not found; skipping $uri"
    return
  fi
  aws s3 rm "$uri" --recursive --region "$region" || true
}

if [[ "${CANCEL_STEP:-true}" == "true" && -n "$cluster_id" && -n "$step_id" && -n "$region" ]] && command -v aws >/dev/null 2>&1; then
  aws emr cancel-steps \
    --cluster-id "$cluster_id" \
    --step-ids "$step_id" \
    --region "$region" >/dev/null 2>&1 || true
fi

remove_s3_prefix "$output_path"
remove_s3_object "$input_path"
remove_s3_object "$job_uri"

if [[ "$context_scenario" =~ ^[A-Za-z0-9_-]+$ ]]; then
  rm -rf "$repo_root/sample-data/generated/$context_scenario"
fi

if [[ "${CLEAN_CONTEXT:-false}" == "true" ]]; then
  rm -f "$context_file"
  last_context="$repo_root/.harrier-demo/last-context.json"
  if [[ "$context_file" != "$last_context" && -f "$last_context" ]]; then
    last_context_scenario="$(
      python3 - "$last_context" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    print(json.load(handle).get("scenario", ""))
PY
    )"
    if [[ "$last_context_scenario" == "$context_scenario" ]]; then
      rm -f "$last_context"
    fi
  fi
fi

echo "Cleaned demo artifacts for $context_scenario using context $context_file"

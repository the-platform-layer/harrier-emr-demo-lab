#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
context_file="${CONTEXT_FILE:-$repo_root/.harrier-demo/last-context.json}"
output_file="${OUTPUT_FILE:-}"
cluster_override="${CLUSTER_ID:-}"
step_override="${STEP_ID:-}"
region_override="${AWS_REGION:-${AWS_DEFAULT_REGION:-}}"
deploy_mode_override="${DEPLOY_MODE:-}"
application_override="${APPLICATION_ID:-}"

while (($# > 0)); do
  case "$1" in
    --context-file)
      context_file="$2"
      shift 2
      ;;
    --output)
      output_file="$2"
      shift 2
      ;;
    --cluster-id)
      cluster_override="$2"
      shift 2
      ;;
    --step-id)
      step_override="$2"
      shift 2
      ;;
    --region)
      region_override="$2"
      shift 2
      ;;
    --deploy-mode)
      deploy_mode_override="$2"
      shift 2
      ;;
    --application-id)
      application_override="$2"
      shift 2
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [[ ! -f "$context_file" ]]; then
  echo "Context file not found: $context_file" >&2
  echo "Run scripts/submit_step.sh first or pass --context-file." >&2
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

cluster_id="${cluster_override:-$(context_value cluster_id)}"
step_id="${step_override:-$(context_value step_id)}"
region="${region_override:-$(context_value region)}"
deploy_mode="${deploy_mode_override:-$(context_value deploy_mode)}"
log_uri="$(context_value log_uri)"

describe_file="$(mktemp)"
trap 'rm -f "$describe_file"' EXIT

if [[ -n "$cluster_id" && -n "$step_id" && -n "$region" ]] && command -v aws >/dev/null 2>&1; then
  aws emr describe-step \
    --cluster-id "$cluster_id" \
    --step-id "$step_id" \
    --region "$region" \
    --output json >"$describe_file" 2>/dev/null || printf '{}\n' >"$describe_file"
else
  printf '{}\n' >"$describe_file"
fi

find_application_id() {
  if [[ -n "$application_override" ]]; then
    echo "$application_override"
    return
  fi

  if [[ -z "$log_uri" || -z "$cluster_id" || -z "$step_id" || -z "$region" ]] || ! command -v aws >/dev/null 2>&1; then
    return
  fi

  local log_root="${log_uri%/}"
  local filename uri match
  for filename in stdout.gz stderr.gz controller.gz syslog.gz stdout stderr controller syslog; do
    uri="$log_root/$cluster_id/steps/$step_id/$filename"
    if [[ "$filename" == *.gz ]]; then
      match="$(aws s3 cp "$uri" - --region "$region" 2>/dev/null | gzip -cd 2>/dev/null | grep -Eo 'application_[0-9]+_[0-9]+' | head -n 1 || true)"
    else
      match="$(aws s3 cp "$uri" - --region "$region" 2>/dev/null | grep -Eo 'application_[0-9]+_[0-9]+' | head -n 1 || true)"
    fi
    if [[ -n "$match" ]]; then
      echo "$match"
      return
    fi
  done
}

application_id="$(find_application_id || true)"

python3 - "$context_file" "$describe_file" "$output_file" "$cluster_id" "$step_id" "$region" \
  "$deploy_mode" "$application_id" <<'PY'
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def normalize_time(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    return str(value).replace("+00:00", "Z")


context_file, describe_file, output_file, cluster_id, step_id, region, deploy_mode, application_id = sys.argv[1:]
with open(context_file, encoding="utf-8") as handle:
    context = json.load(handle)
with open(describe_file, encoding="utf-8") as handle:
    describe = json.load(handle)

step = describe.get("Step", {})
status = step.get("Status", {})
timeline = status.get("Timeline", {})
context_window = context.get("time_window") or {}
default_start = datetime.now(timezone.utc) - timedelta(minutes=30)
state = status.get("State")
state_map = {
    "PENDING": "running",
    "CANCEL_PENDING": "running",
    "RUNNING": "running",
    "COMPLETED": "completed",
    "CANCELLED": "failed",
    "FAILED": "failed",
    "INTERRUPTED": "failed",
}
job_state = state_map.get(state, context.get("job_state", "unknown"))

start_time = (
    normalize_time(timeline.get("StartDateTime"))
    or normalize_time(timeline.get("CreationDateTime"))
    or context_window.get("start")
    or default_start.isoformat().replace("+00:00", "Z")
)
end_time = (
    normalize_time(timeline.get("EndDateTime"))
    or context_window.get("end")
    or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
)

payload = {
    "scenario": context.get("scenario", "happy_path"),
    "region": region or context.get("region"),
    "cluster_id": cluster_id or context.get("cluster_id"),
    "deploy_mode": deploy_mode or context.get("deploy_mode", "unknown"),
    "job_state": job_state,
    "step_id": step_id or context.get("step_id"),
    "application_id": application_id or context.get("application_id"),
    "time_window": {
        "start": start_time,
        "end": end_time,
    },
    "log_uri": context.get("log_uri"),
    "input_path": context.get("input_path"),
    "output_path": context.get("output_path"),
    "diagnostic_signals": context.get("diagnostic_signals"),
    "expected_outcome": context.get("expected_outcome", "success"),
    "aws_step_status": status.get("State"),
}

encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
if output_file:
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    Path(output_file).write_text(encoded, encoding="utf-8")
else:
    print(encoded, end="")
PY

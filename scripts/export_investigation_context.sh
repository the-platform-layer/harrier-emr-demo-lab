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
runtime_override="${RUNTIME:-${HARRIER_RUNTIME:-}}"
serverless_application_override="${EMR_SERVERLESS_APPLICATION_ID:-}"
job_run_override="${JOB_RUN_ID:-}"
attempt_override="${ATTEMPT:-}"
eks_virtual_cluster_override="${EMR_EKS_VIRTUAL_CLUSTER_ID:-${VIRTUAL_CLUSTER_ID:-}}"
eks_job_run_override="${EMR_EKS_JOB_RUN_ID:-}"
eks_cluster_override="${EMR_EKS_CLUSTER_NAME:-${EKS_CLUSTER_NAME:-}}"
eks_namespace_override="${EMR_EKS_NAMESPACE:-}"

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
    --runtime)
      runtime_override="$2"
      shift 2
      ;;
    --serverless-application-id)
      serverless_application_override="$2"
      shift 2
      ;;
    --job-run-id)
      job_run_override="$2"
      eks_job_run_override="$2"
      shift 2
      ;;
    --attempt)
      attempt_override="$2"
      shift 2
      ;;
    --virtual-cluster-id)
      eks_virtual_cluster_override="$2"
      shift 2
      ;;
    --eks-cluster-name)
      eks_cluster_override="$2"
      shift 2
      ;;
    --namespace)
      eks_namespace_override="$2"
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
runtime="${runtime_override:-$(context_value runtime)}"
runtime="${runtime:-emr_ec2}"

normalize_s3_uri() {
  case "$1" in
    s3n://*) printf 's3://%s\n' "${1#s3n://}" ;;
    s3a://*) printf 's3://%s\n' "${1#s3a://}" ;;
    *) printf '%s\n' "$1" ;;
  esac
}

describe_file="$(mktemp)"
trap 'rm -f "$describe_file"' EXIT

if [[ "$runtime" == "emr_eks" || "$runtime" == "eks" ]]; then
  virtual_cluster_id="${eks_virtual_cluster_override:-$(context_value virtual_cluster_id)}"
  job_run_id="${eks_job_run_override:-${job_run_override:-$(context_value job_run_id)}}"
  eks_cluster_name="${eks_cluster_override:-$(context_value eks_cluster_name)}"
  namespace="${eks_namespace_override:-$(context_value namespace)}"

  if [[ -n "$virtual_cluster_id" && -n "$job_run_id" && -n "$region" ]] && command -v aws >/dev/null 2>&1; then
    aws emr-containers describe-job-run \
      --virtual-cluster-id "$virtual_cluster_id" \
      --id "$job_run_id" \
      --region "$region" \
      --output json >"$describe_file" 2>/dev/null || printf '{}\n' >"$describe_file"
  else
    printf '{}\n' >"$describe_file"
  fi

  python3 - "$context_file" "$describe_file" "$output_file" "$virtual_cluster_id" \
    "$job_run_id" "$region" "$eks_cluster_name" "$namespace" <<'PY'
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


context_file, describe_file, output_file, virtual_cluster_id, job_run_id, region, cluster_name, namespace = sys.argv[1:]
with open(context_file, encoding="utf-8") as handle:
    context = json.load(handle)
with open(describe_file, encoding="utf-8") as handle:
    describe = json.load(handle)

job_run = describe.get("jobRun", {})
state = job_run.get("state")
state_map = {
    "PENDING": "running",
    "SUBMITTED": "running",
    "RUNNING": "running",
    "CANCEL_PENDING": "failed",
    "COMPLETED": "completed",
    "FAILED": "failed",
    "CANCELLED": "failed",
}
job_state = state_map.get(state, context.get("job_state", "unknown"))
context_window = context.get("time_window") or {}
default_start = datetime.now(timezone.utc) - timedelta(minutes=30)

start_time = (
    normalize_time(job_run.get("createdAt"))
    or context_window.get("start")
    or default_start.isoformat().replace("+00:00", "Z")
)
end_time = (
    normalize_time(job_run.get("finishedAt"))
    or context_window.get("end")
    or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
)

overrides = job_run.get("configurationOverrides") or {}
monitoring = overrides.get("monitoringConfiguration") or {}
s3_monitoring = monitoring.get("s3MonitoringConfiguration") or {}
cloudwatch = monitoring.get("cloudWatchMonitoringConfiguration") or {}

resolved_virtual_cluster_id = (
    virtual_cluster_id
    or context.get("virtual_cluster_id")
    or job_run.get("virtualClusterId")
)
resolved_job_run_id = job_run_id or context.get("job_run_id") or job_run.get("id")
resolved_cluster_name = cluster_name or context.get("eks_cluster_name")
resolved_namespace = namespace or context.get("namespace")

target = {
    "virtual_cluster_id": resolved_virtual_cluster_id,
    "job_run_id": resolved_job_run_id,
}
if resolved_cluster_name:
    target["eks_cluster_name"] = resolved_cluster_name
if resolved_namespace:
    target["namespace"] = resolved_namespace

payload = {
    "scenario": context.get("scenario", "happy_path"),
    "region": region or context.get("region"),
    "runtime": "emr_eks",
    "target": target,
    "virtual_cluster_id": resolved_virtual_cluster_id,
    "job_run_id": resolved_job_run_id,
    "eks_cluster_name": resolved_cluster_name,
    "namespace": resolved_namespace,
    "job_state": job_state,
    "time_window": {
        "start": start_time,
        "end": end_time,
    },
    "log_uri": s3_monitoring.get("logUri") or context.get("log_uri"),
    "cloudwatch_log_group": cloudwatch.get("logGroupName") or context.get("cloudwatch_log_group"),
    "cloudwatch_log_stream_prefix": (
        cloudwatch.get("logStreamNamePrefix") or context.get("cloudwatch_log_stream_prefix")
    ),
    "input_path": context.get("input_path"),
    "output_path": context.get("output_path"),
    "job_uri": context.get("job_uri"),
    "diagnostic_signals": context.get("diagnostic_signals"),
    "expected_outcome": context.get("expected_outcome", "success"),
    "aws_job_run_state": state,
    "state_details": job_run.get("stateDetails"),
    "failure_reason": job_run.get("failureReason"),
    "release_label": job_run.get("releaseLabel") or context.get("release_label"),
}

encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
if output_file:
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    Path(output_file).write_text(encoded, encoding="utf-8")
else:
    print(encoded, end="")
PY
  exit 0
fi

if [[ "$runtime" == "emr_serverless" || "$runtime" == "serverless" ]]; then
  serverless_application_id="${serverless_application_override:-$(context_value serverless_application_id)}"
  job_run_id="${job_run_override:-$(context_value job_run_id)}"
  attempt="${attempt_override:-$(context_value attempt)}"

  if [[ -n "$serverless_application_id" && -n "$job_run_id" && -n "$region" ]] && command -v aws >/dev/null 2>&1; then
    aws emr-serverless get-job-run \
      --application-id "$serverless_application_id" \
      --job-run-id "$job_run_id" \
      --region "$region" \
      --output json >"$describe_file" 2>/dev/null || printf '{}\n' >"$describe_file"
  else
    printf '{}\n' >"$describe_file"
  fi

  python3 - "$context_file" "$describe_file" "$output_file" "$serverless_application_id" \
    "$job_run_id" "$region" "$attempt" <<'PY'
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


context_file, describe_file, output_file, application_id, job_run_id, region, attempt = sys.argv[1:]
with open(context_file, encoding="utf-8") as handle:
    context = json.load(handle)
with open(describe_file, encoding="utf-8") as handle:
    describe = json.load(handle)

job_run = describe.get("jobRun", {})
state = job_run.get("state")
state_map = {
    "PENDING": "running",
    "SCHEDULED": "running",
    "SUBMITTED": "running",
    "RUNNING": "running",
    "SUCCESS": "completed",
    "FAILED": "failed",
    "CANCELLING": "failed",
    "CANCELLED": "failed",
}
job_state = state_map.get(state, context.get("job_state", "unknown"))
context_window = context.get("time_window") or {}
default_start = datetime.now(timezone.utc) - timedelta(minutes=30)

start_time = (
    normalize_time(job_run.get("startedAt"))
    or normalize_time(job_run.get("createdAt"))
    or context_window.get("start")
    or default_start.isoformat().replace("+00:00", "Z")
)
end_time = (
    normalize_time(job_run.get("endedAt"))
    or normalize_time(job_run.get("updatedAt"))
    or context_window.get("end")
    or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
)

overrides = job_run.get("configurationOverrides") or {}
monitoring = overrides.get("monitoringConfiguration") or {}
s3_monitoring = monitoring.get("s3MonitoringConfiguration") or {}
cloudwatch = monitoring.get("cloudWatchLoggingConfiguration") or {}

resolved_application_id = application_id or context.get("serverless_application_id") or job_run.get("applicationId")
resolved_job_run_id = job_run_id or context.get("job_run_id") or job_run.get("jobRunId")
resolved_attempt = attempt or context.get("attempt") or job_run.get("attempt")
target = {
    "serverless_application_id": resolved_application_id,
    "job_run_id": resolved_job_run_id,
}
if resolved_attempt not in (None, ""):
    target["attempt"] = int(resolved_attempt)

payload = {
    "scenario": context.get("scenario", "happy_path"),
    "region": region or context.get("region"),
    "runtime": "emr_serverless",
    "target": target,
    "serverless_application_id": resolved_application_id,
    "job_run_id": resolved_job_run_id,
    "attempt": resolved_attempt,
    "job_state": job_state,
    "time_window": {
        "start": start_time,
        "end": end_time,
    },
    "log_uri": s3_monitoring.get("logUri") or context.get("log_uri"),
    "cloudwatch_log_group": cloudwatch.get("logGroupName") or context.get("cloudwatch_log_group"),
    "cloudwatch_log_stream_prefix": (
        cloudwatch.get("logStreamNamePrefix") or context.get("cloudwatch_log_stream_prefix")
    ),
    "input_path": context.get("input_path"),
    "output_path": context.get("output_path"),
    "job_uri": context.get("job_uri"),
    "diagnostic_signals": context.get("diagnostic_signals"),
    "expected_outcome": context.get("expected_outcome", "success"),
    "aws_job_run_state": state,
    "state_details": job_run.get("stateDetails"),
    "release_label": job_run.get("releaseLabel"),
}

encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
if output_file:
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    Path(output_file).write_text(encoded, encoding="utf-8")
else:
    print(encoded, end="")
PY
  exit 0
fi

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

  local log_root
  log_root="$(normalize_s3_uri "${log_uri%/}")"
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

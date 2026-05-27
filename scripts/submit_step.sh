#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
tf_dir="$repo_root/infra/terraform"

scenario="${SCENARIO:-${1:-happy_path}}"
run_id="${RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
rows="${ROWS:-1000}"
deploy_mode="${DEPLOY_MODE:-cluster}"

if [[ "$deploy_mode" != "client" && "$deploy_mode" != "cluster" ]]; then
  echo "DEPLOY_MODE must be client or cluster" >&2
  exit 2
fi

tf_json="$(terraform -chdir="$tf_dir" output -json 2>/dev/null || printf '{}')"

tf_output() {
  TF_JSON="$tf_json" python3 - "$1" <<'PY'
import json
import os
import sys

name = sys.argv[1]
try:
    data = json.loads(os.environ.get("TF_JSON", "{}"))
except json.JSONDecodeError:
    data = {}

value = data.get(name, {}).get("value", "")
if value is None:
    value = ""
print(value)
PY
}

cluster_id="${CLUSTER_ID:-$(tf_output cluster_id)}"
region="${AWS_REGION:-${AWS_DEFAULT_REGION:-$(tf_output region)}}"
raw_bucket="${RAW_BUCKET:-$(tf_output raw_bucket)}"
processed_bucket="${PROCESSED_BUCKET:-$(tf_output processed_bucket)}"
log_uri="${LOG_URI:-$(tf_output log_uri)}"

missing=()
[[ -z "$cluster_id" ]] && missing+=("CLUSTER_ID or terraform output cluster_id")
[[ -z "$region" ]] && missing+=("AWS_REGION/AWS_DEFAULT_REGION or terraform output region")
[[ -z "$raw_bucket" ]] && missing+=("RAW_BUCKET or terraform output raw_bucket")
[[ -z "$processed_bucket" ]] && missing+=("PROCESSED_BUCKET or terraform output processed_bucket")

if ((${#missing[@]} > 0)); then
  echo "Missing required values:" >&2
  printf '  - %s\n' "${missing[@]}" >&2
  echo "Run Terraform first or provide the values as environment variables." >&2
  exit 2
fi

job_file="$repo_root/spark-jobs/$scenario/job.py"
if [[ ! -f "$job_file" ]]; then
  echo "Scenario job not found: $job_file" >&2
  exit 2
fi

job_s3_uri="${JOB_S3_URI:-s3://$raw_bucket/code/$scenario/$run_id/job.py}"
output_s3_uri="${OUTPUT_S3_URI:-s3://$processed_bucket/$scenario/$run_id}"
data_s3_uri="${DATA_S3_URI:-}"
expected_outcome="running"
diagnostic_signals_json="{}"
spark_args=("spark-submit" "--deploy-mode" "$deploy_mode")

case "$scenario" in
  happy_path)
    expected_outcome="success"
    local_data_file="${LOCAL_DATA_FILE:-$repo_root/sample-data/generated/happy_path/events-$run_id.csv}"
    data_s3_uri="${data_s3_uri:-s3://$raw_bucket/input/happy_path/$run_id/events.csv}"
    python3 "$repo_root/scripts/generate_data.py" --rows "$rows" --output "$local_data_file"
    aws s3 cp "$local_data_file" "$data_s3_uri" --region "$region"
    spark_args+=(
      "$job_s3_uri"
      "--input" "$data_s3_uri"
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
    )
    ;;
  long_running_data_delay)
    hot_sleep_seconds="${HOT_PARTITION_SLEEP_SECONDS:-900}"
    partitions="${PARTITIONS:-24}"
    hot_rows="${HOT_ROWS:-200000}"
    cold_rows="${ROWS_PER_COLD_PARTITION:-2000}"
    diagnostic_signals_json="$(
      python3 - "$hot_sleep_seconds" <<'PY'
import json
import sys

hot_sleep = float(sys.argv[1])
print(json.dumps({
    "active_stage_count": 1,
    "active_task_count": 1,
    "max_task_runtime_minutes": round(hot_sleep / 60, 2),
    "median_task_runtime_minutes": 1,
    "skew_ratio": 12,
    "shuffle_spill_mb": 1536,
}))
PY
    )"
    spark_args+=(
      "$job_s3_uri"
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
      "--partitions" "$partitions"
      "--hot-partition-sleep-seconds" "$hot_sleep_seconds"
      "--hot-rows" "$hot_rows"
      "--rows-per-cold-partition" "$cold_rows"
    )
    ;;
  long_running_resource_delay)
    tasks="${TASKS:-96}"
    sleep_seconds="${SLEEP_SECONDS:-900}"
    executor_instances="${EXECUTOR_INSTANCES:-20}"
    executor_memory="${EXECUTOR_MEMORY:-4g}"
    executor_cores="${EXECUTOR_CORES:-2}"
    diagnostic_signals_json="$(
      python3 - "$executor_instances" <<'PY'
import json
import sys

instances = int(sys.argv[1])
print(json.dumps({
    "active_stage_count": 1,
    "active_task_count": instances,
    "pending_containers": max(1, instances // 2),
    "yarn_memory_available_percent": 5,
}))
PY
    )"
    spark_args+=(
      "--conf" "spark.dynamicAllocation.enabled=false"
      "--conf" "spark.executor.instances=$executor_instances"
      "--executor-memory" "$executor_memory"
      "--executor-cores" "$executor_cores"
      "$job_s3_uri"
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
      "--tasks" "$tasks"
      "--sleep-seconds" "$sleep_seconds"
    )
    ;;
  long_running_db_delay)
    db_sleep_seconds="${DB_SLEEP_SECONDS:-900}"
    db_secret_id="${DB_SECRET_ID:-}"
    jdbc_url="${JDBC_URL:-}"
    db_user="${DB_USER:-}"
    postgres_package="${POSTGRES_JDBC_PACKAGE:-org.postgresql:postgresql:42.7.4}"
    diagnostic_signals_json="$(
      python3 - "$db_sleep_seconds" <<'PY'
import json
import sys

sleep_seconds = float(sys.argv[1])
print(json.dumps({
    "jdbc_stage_active": True,
    "active_db_query_seconds": sleep_seconds,
    "db_wait_event": "ClientRead or IO wait from demo query",
    "db_plan_summary": "long-running PostgreSQL pg_sleep demo query",
}))
PY
    )"
    if [[ -z "$db_secret_id" && -z "$jdbc_url" ]]; then
      echo "long_running_db_delay requires DB_SECRET_ID or JDBC_URL." >&2
      echo "Use DB_SECRET_ID for demo-safe credential injection through Secrets Manager." >&2
      exit 2
    fi
    spark_args+=("--packages" "$postgres_package")
    [[ -n "$db_secret_id" ]] && spark_args+=("--conf" "spark.yarn.appMasterEnv.HARRIER_DB_SECRET_ID=$db_secret_id")
    [[ -n "$jdbc_url" ]] && spark_args+=("--conf" "spark.yarn.appMasterEnv.HARRIER_JDBC_URL=$jdbc_url")
    [[ -n "$db_user" ]] && spark_args+=("--conf" "spark.yarn.appMasterEnv.HARRIER_DB_USER=$db_user")
    spark_args+=(
      "$job_s3_uri"
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
      "--sleep-seconds" "$db_sleep_seconds"
    )
    ;;
  *)
    echo "Unsupported scenario for submit_step.sh: $scenario" >&2
    exit 2
    ;;
esac

aws s3 cp "$job_file" "$job_s3_uri" --region "$region"

step_file="$(mktemp)"
trap 'rm -f "$step_file"' EXIT

python3 - "$step_file" "$scenario" "$run_id" "${spark_args[@]}" <<'PY'
import json
import sys
from pathlib import Path

step_file, scenario, run_id, *spark_args = sys.argv[1:]
step = [
    {
        "Name": f"harrier-demo-{scenario}-{run_id}",
        "ActionOnFailure": "CONTINUE",
        "HadoopJarStep": {
            "Jar": "command-runner.jar",
            "Args": spark_args,
        },
    }
]
Path(step_file).write_text(json.dumps(step, indent=2) + "\n", encoding="utf-8")
PY

step_id="$(
  aws emr add-steps \
    --cluster-id "$cluster_id" \
    --region "$region" \
    --steps "file://$step_file" \
    --query 'StepIds[0]' \
    --output text
)"

submitted_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
context_dir="$repo_root/.harrier-demo/runs"
context_file="${CONTEXT_FILE:-$repo_root/.harrier-demo/last-context.json}"
run_context_file="$context_dir/$scenario-$run_id.json"
mkdir -p "$context_dir" "$(dirname "$context_file")"

python3 - "$context_file" "$run_context_file" "$scenario" "$run_id" "$region" "$cluster_id" \
  "$deploy_mode" "$step_id" "$data_s3_uri" "$output_s3_uri" "$job_s3_uri" "$log_uri" \
  "$expected_outcome" "$diagnostic_signals_json" "$submitted_at" <<'PY'
import json
import sys
from pathlib import Path

(
    context_file,
    run_context_file,
    scenario,
    run_id,
    region,
    cluster_id,
    deploy_mode,
    step_id,
    data_s3_uri,
    output_s3_uri,
    job_s3_uri,
    log_uri,
    expected_outcome,
    diagnostic_signals_json,
    submitted_at,
) = sys.argv[1:]

diagnostic_signals = json.loads(diagnostic_signals_json or "{}")
context = {
    "scenario": scenario,
    "run_id": run_id,
    "region": region,
    "cluster_id": cluster_id,
    "deploy_mode": deploy_mode,
    "job_state": "running",
    "step_id": step_id,
    "application_id": None,
    "time_window": {
        "start": submitted_at,
        "end": None,
    },
    "input_path": data_s3_uri or None,
    "output_path": output_s3_uri,
    "job_uri": job_s3_uri,
    "log_uri": log_uri,
    "expected_outcome": expected_outcome,
    "diagnostic_signals": diagnostic_signals or None,
    "submitted_at": submitted_at,
}

payload = json.dumps(context, indent=2, sort_keys=True) + "\n"
Path(context_file).write_text(payload, encoding="utf-8")
Path(run_context_file).write_text(payload, encoding="utf-8")
PY

echo "Submitted $scenario step $step_id to cluster $cluster_id"
echo "Context: $context_file"

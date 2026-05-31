#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
tf_dir="$repo_root/infra/terraform"

scenario="${SCENARIO:-${1:-happy_path}}"
run_id="${RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
rows="${ROWS:-1000}"

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

application_id="${EMR_SERVERLESS_APPLICATION_ID:-$(tf_output emr_serverless_application_id)}"
execution_role_arn="${EMR_SERVERLESS_JOB_ROLE_ARN:-$(tf_output emr_serverless_job_role_arn)}"
region="${AWS_REGION:-${AWS_DEFAULT_REGION:-$(tf_output region)}}"
raw_bucket="${RAW_BUCKET:-$(tf_output raw_bucket)}"
processed_bucket="${PROCESSED_BUCKET:-$(tf_output processed_bucket)}"
logs_bucket="${LOGS_BUCKET:-$(tf_output logs_bucket)}"
log_group="${EMR_SERVERLESS_LOG_GROUP:-$(tf_output emr_serverless_log_group)}"
log_uri="${LOG_URI:-$(tf_output emr_serverless_log_uri)}"
log_uri="${log_uri:-s3://$logs_bucket/emr-serverless/}"
log_stream_prefix="${EMR_SERVERLESS_LOG_STREAM_PREFIX:-harrier-demo/$scenario/$run_id}"

missing=()
[[ -z "$application_id" ]] && missing+=("EMR_SERVERLESS_APPLICATION_ID or terraform output emr_serverless_application_id")
[[ -z "$execution_role_arn" ]] && missing+=("EMR_SERVERLESS_JOB_ROLE_ARN or terraform output emr_serverless_job_role_arn")
[[ -z "$region" ]] && missing+=("AWS_REGION/AWS_DEFAULT_REGION or terraform output region")
[[ -z "$raw_bucket" ]] && missing+=("RAW_BUCKET or terraform output raw_bucket")
[[ -z "$processed_bucket" ]] && missing+=("PROCESSED_BUCKET or terraform output processed_bucket")
[[ -z "$logs_bucket" && -z "$log_uri" ]] && missing+=("LOGS_BUCKET or terraform output logs_bucket")

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

job_s3_uri="${JOB_S3_URI:-s3://$raw_bucket/code/emr_serverless/$scenario/$run_id/job.py}"
output_s3_uri="${OUTPUT_S3_URI:-s3://$processed_bucket/emr_serverless/$scenario/$run_id}"
data_s3_uri="${DATA_S3_URI:-}"
expected_outcome="running"
diagnostic_signals_json="{}"
entry_args=()
spark_submit_params=(
  "--conf" "spark.sql.session.timeZone=UTC"
  "--conf" "spark.dynamicAllocation.enabled=false"
  "--conf" "spark.executor.instances=${SERVERLESS_EXECUTOR_INSTANCES:-1}"
  "--conf" "spark.executor.cores=${SERVERLESS_EXECUTOR_CORES:-1}"
  "--conf" "spark.executor.memory=${SERVERLESS_EXECUTOR_MEMORY:-2g}"
  "--conf" "spark.driver.cores=${SERVERLESS_DRIVER_CORES:-1}"
  "--conf" "spark.driver.memory=${SERVERLESS_DRIVER_MEMORY:-2g}"
)

case "$scenario" in
  happy_path)
    expected_outcome="success"
    local_data_file="${LOCAL_DATA_FILE:-$repo_root/sample-data/generated/emr_serverless/happy_path/events-$run_id.csv}"
    data_s3_uri="${data_s3_uri:-s3://$raw_bucket/input/emr_serverless/happy_path/$run_id/events.csv}"
    python3 "$repo_root/scripts/generate_data.py" --rows "$rows" --output "$local_data_file"
    aws s3 cp "$local_data_file" "$data_s3_uri" --region "$region"
    entry_args+=(
      "--input" "$data_s3_uri"
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
    )
    ;;
  executor_oom)
    expected_outcome="failed"
    executor_instances="${EXECUTOR_INSTANCES:-2}"
    executor_memory="${EXECUTOR_MEMORY:-1g}"
    executor_memory_overhead="${EXECUTOR_MEMORY_OVERHEAD:-384}"
    executor_cores="${EXECUTOR_CORES:-1}"
    partitions="${PARTITIONS:-4}"
    allocation_mb="${EXECUTOR_OOM_ALLOCATION_MB:-768}"
    diagnostic_signals_json="$(
      python3 - "$allocation_mb" <<'PY'
import json
import sys

allocation_mb = int(sys.argv[1])
print(json.dumps({
    "root_cause_hint": "EXECUTOR_OOM",
    "executor_memory_allocation_mb": allocation_mb,
    "log_signal": (
        "executor 0 java.lang.OutOfMemoryError: Java heap space; "
        "container killed by YARN for exceeding physical memory"
    ),
}))
PY
    )"
    spark_submit_params=(
      "--conf" "spark.dynamicAllocation.enabled=false"
      "--conf" "spark.executor.instances=$executor_instances"
      "--conf" "spark.executor.cores=$executor_cores"
      "--conf" "spark.executor.memory=$executor_memory"
      "--conf" "spark.executor.memoryOverhead=$executor_memory_overhead"
      "--conf" "spark.task.maxFailures=1"
      "--conf" "spark.excludeOnFailure.enabled=false"
      "--conf" "spark.driver.cores=1"
      "--conf" "spark.driver.memory=2g"
    )
    entry_args+=(
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
      "--partitions" "$partitions"
      "--allocation-mb" "$allocation_mb"
    )
    ;;
  missing_dependency)
    expected_outcome="failed"
    missing_module="${MISSING_MODULE:-harrier_demo_missing_dependency}"
    diagnostic_signals_json="$(
      python3 - "$missing_module" <<'PY'
import json
import sys

module = sys.argv[1]
print(json.dumps({
    "root_cause_hint": "DEPENDENCY_MISSING",
    "missing_module": module,
    "log_signal": f"ModuleNotFoundError: No module named {module}",
}))
PY
    )"
    entry_args+=(
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
      "--module" "$missing_module"
    )
    ;;
  s3_path_missing)
    expected_outcome="failed"
    missing_s3_uri="${MISSING_INPUT_URI:-s3://$raw_bucket/input/emr_serverless/s3_path_missing/$run_id/missing.parquet}"
    data_s3_uri="$missing_s3_uri"
    diagnostic_signals_json="$(
      python3 - "$missing_s3_uri" <<'PY'
import json
import sys

uri = sys.argv[1]
print(json.dumps({
    "root_cause_hint": "S3_PATH_MISSING",
    "missing_input_uri": uri,
    "log_signal": f"NoSuchKey: The specified key does not exist at {uri}",
}))
PY
    )"
    entry_args+=(
      "--missing-input" "$missing_s3_uri"
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
    )
    ;;
  bad_input_data)
    expected_outcome="failed"
    local_data_file="${LOCAL_DATA_FILE:-$repo_root/sample-data/generated/emr_serverless/bad_input_data/events-$run_id.csv}"
    data_s3_uri="${data_s3_uri:-s3://$raw_bucket/input/emr_serverless/bad_input_data/$run_id/events.csv}"
    python3 - "$local_data_file" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(
    "event_id,customer_id,amount,event_ts,country\n"
    "evt-0001,cust-0001,42.75,2026-01-01T00:00:00Z,AU\n"
    "evt-0002,cust-0002,not-a-number,2026-01-01T00:01:00Z,US\n"
    "evt-0003,cust-0003,18.10,not-a-timestamp,GB\n",
    encoding="utf-8",
)
PY
    aws s3 cp "$local_data_file" "$data_s3_uri" --region "$region"
    diagnostic_signals_json="$(
      python3 - "$data_s3_uri" <<'PY'
import json
import sys

uri = sys.argv[1]
print(json.dumps({
    "root_cause_hint": "BAD_INPUT_DATA",
    "bad_input_uri": uri,
    "log_signal": "CSV malformed; schema mismatch with corrupt record",
}))
PY
    )"
    entry_args+=(
      "--input" "$data_s3_uri"
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
    )
    ;;
  *)
    echo "EMR Serverless scenario is not implemented yet: $scenario" >&2
    echo "Supported: happy_path, executor_oom, missing_dependency, s3_path_missing, bad_input_data" >&2
    exit 2
    ;;
esac

aws s3 cp "$job_file" "$job_s3_uri" --region "$region"

job_driver_file="$(mktemp)"
configuration_file="$(mktemp)"
trap 'rm -f "$job_driver_file" "$configuration_file"' EXIT

python3 - "$job_driver_file" "$job_s3_uri" "${spark_submit_params[*]}" "${entry_args[@]}" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
entry_point = sys.argv[2]
spark_submit_parameters = sys.argv[3]
entry_point_arguments = sys.argv[4:]

path.write_text(
    json.dumps(
        {
            "sparkSubmit": {
                "entryPoint": entry_point,
                "entryPointArguments": entry_point_arguments,
                "sparkSubmitParameters": spark_submit_parameters,
            }
        },
        indent=2,
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)
PY

python3 - "$configuration_file" "$log_uri" "$log_group" "$log_stream_prefix" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
log_uri, log_group, log_stream_prefix = sys.argv[2:]

monitoring = {
    "s3MonitoringConfiguration": {
        "logUri": log_uri,
    }
}

if log_group:
    monitoring["cloudWatchLoggingConfiguration"] = {
        "enabled": True,
        "logGroupName": log_group,
        "logStreamNamePrefix": log_stream_prefix,
        "logTypes": {
            "SPARK_DRIVER": ["STDOUT", "STDERR"],
            "SPARK_EXECUTOR": ["STDOUT", "STDERR"],
        },
    }

path.write_text(
    json.dumps({"monitoringConfiguration": monitoring}, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY

job_name="harrier-demo-sl-$scenario-$run_id"
job_run_id="$(
  aws emr-serverless start-job-run \
    --application-id "$application_id" \
    --client-token "$run_id" \
    --execution-role-arn "$execution_role_arn" \
    --name "$job_name" \
    --job-driver "file://$job_driver_file" \
    --configuration-overrides "file://$configuration_file" \
    --region "$region" \
    --query jobRunId \
    --output text
)"

context_dir="$repo_root/.harrier-demo"
mkdir -p "$context_dir/runs"
context_file="${CONTEXT_FILE:-$context_dir/last-context.json}"

python3 - "$context_file" "$context_dir/runs/$scenario-$run_id.json" <<PY
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

diagnostic_signals = json.loads("""$diagnostic_signals_json""")
start = datetime.now(timezone.utc) - timedelta(minutes=10)
end = datetime.now(timezone.utc) + timedelta(minutes=45)

payload = {
    "scenario": "$scenario",
    "run_id": "$run_id",
    "region": "$region",
    "runtime": "emr_serverless",
    "serverless_application_id": "$application_id",
    "job_run_id": "$job_run_id",
    "attempt": None,
    "target": {
        "serverless_application_id": "$application_id",
        "job_run_id": "$job_run_id",
    },
    "job_state": "running",
    "time_window": {
        "start": start.isoformat().replace("+00:00", "Z"),
        "end": end.isoformat().replace("+00:00", "Z"),
    },
    "input_path": "$data_s3_uri",
    "output_path": "$output_s3_uri",
    "job_uri": "$job_s3_uri",
    "log_uri": "$log_uri",
    "cloudwatch_log_group": "$log_group",
    "cloudwatch_log_stream_prefix": "$log_stream_prefix",
    "expected_outcome": "$expected_outcome",
    "diagnostic_signals": diagnostic_signals,
    "submitted_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
}

encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
for path in (Path("$context_file"), Path("$context_dir/runs/$scenario-$run_id.json")):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(encoded, encoding="utf-8")
PY

echo "Submitted EMR Serverless job run $job_run_id for scenario $scenario"
echo "Context written to $context_file"

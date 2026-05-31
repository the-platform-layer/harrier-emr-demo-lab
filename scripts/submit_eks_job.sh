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

virtual_cluster_id="${EMR_EKS_VIRTUAL_CLUSTER_ID:-$(tf_output emr_eks_virtual_cluster_id)}"
execution_role_arn="${EMR_EKS_JOB_ROLE_ARN:-$(tf_output emr_eks_job_role_arn)}"
release_label="${EMR_EKS_RELEASE_LABEL:-$(tf_output emr_eks_release_label)}"
eks_cluster_name="${EMR_EKS_CLUSTER_NAME:-${EKS_CLUSTER_NAME:-$(tf_output emr_eks_cluster_name)}}"
namespace="${EMR_EKS_NAMESPACE:-$(tf_output emr_eks_namespace)}"
region="${AWS_REGION:-${AWS_DEFAULT_REGION:-$(tf_output region)}}"
raw_bucket="${RAW_BUCKET:-$(tf_output raw_bucket)}"
processed_bucket="${PROCESSED_BUCKET:-$(tf_output processed_bucket)}"
logs_bucket="${LOGS_BUCKET:-$(tf_output logs_bucket)}"
log_group="${EMR_EKS_LOG_GROUP:-$(tf_output emr_eks_log_group)}"
log_uri="${LOG_URI:-$(tf_output emr_eks_log_uri)}"
log_uri="${log_uri:-s3://$logs_bucket/emr-eks/}"
log_stream_prefix="${EMR_EKS_LOG_STREAM_PREFIX:-harrier-demo/$scenario/$run_id}"
bad_image_uri="${EMR_EKS_BAD_IMAGE_URI:-$(tf_output emr_eks_bad_image_uri)}"

missing=()
[[ -z "$virtual_cluster_id" ]] && missing+=("EMR_EKS_VIRTUAL_CLUSTER_ID or terraform output emr_eks_virtual_cluster_id")
[[ -z "$execution_role_arn" ]] && missing+=("EMR_EKS_JOB_ROLE_ARN or terraform output emr_eks_job_role_arn")
[[ -z "$release_label" ]] && missing+=("EMR_EKS_RELEASE_LABEL or terraform output emr_eks_release_label")
[[ -z "$eks_cluster_name" ]] && missing+=("EMR_EKS_CLUSTER_NAME/EKS_CLUSTER_NAME or terraform output emr_eks_cluster_name")
[[ -z "$namespace" ]] && missing+=("EMR_EKS_NAMESPACE or terraform output emr_eks_namespace")
[[ -z "$region" ]] && missing+=("AWS_REGION/AWS_DEFAULT_REGION or terraform output region")
[[ -z "$raw_bucket" ]] && missing+=("RAW_BUCKET or terraform output raw_bucket")
[[ -z "$processed_bucket" ]] && missing+=("PROCESSED_BUCKET or terraform output processed_bucket")
[[ -z "$logs_bucket" && -z "$log_uri" ]] && missing+=("LOGS_BUCKET or terraform output logs_bucket")

if ((${#missing[@]} > 0)); then
  echo "Missing required values:" >&2
  printf '  - %s\n' "${missing[@]}" >&2
  echo "Run Terraform and scripts/setup_eks_virtual_cluster.sh first, or provide the values as environment variables." >&2
  exit 2
fi

job_scenario="$scenario"
job_file="$repo_root/spark-jobs/$job_scenario/job.py"
case "$scenario" in
  image_pull_failure)
    job_scenario="missing_dependency"
    job_file="$repo_root/spark-jobs/$job_scenario/job.py"
    ;;
  pod_pending_resource_pressure)
    job_scenario="happy_path"
    job_file="$repo_root/spark-jobs/$job_scenario/job.py"
    ;;
esac

if [[ ! -f "$job_file" ]]; then
  echo "Scenario job not found: $job_file" >&2
  exit 2
fi

job_s3_uri="${JOB_S3_URI:-s3://$raw_bucket/code/emr_eks/$scenario/$run_id/job.py}"
output_s3_uri="${OUTPUT_S3_URI:-s3://$processed_bucket/emr_eks/$scenario/$run_id}"
data_s3_uri="${DATA_S3_URI:-}"
expected_outcome="running"
diagnostic_signals_json="{}"
application_config_json="[]"
entry_args=()
spark_submit_params=(
  "--conf" "spark.sql.session.timeZone=UTC"
  "--conf" "spark.dynamicAllocation.enabled=false"
  "--conf" "spark.executor.instances=${EKS_EXECUTOR_INSTANCES:-1}"
  "--conf" "spark.executor.cores=${EKS_EXECUTOR_CORES:-1}"
  "--conf" "spark.executor.memory=${EKS_EXECUTOR_MEMORY:-2g}"
  "--conf" "spark.driver.cores=${EKS_DRIVER_CORES:-1}"
  "--conf" "spark.driver.memory=${EKS_DRIVER_MEMORY:-2g}"
)

case "$scenario" in
  happy_path)
    expected_outcome="success"
    local_data_file="${LOCAL_DATA_FILE:-$repo_root/sample-data/generated/emr_eks/happy_path/events-$run_id.csv}"
    data_s3_uri="${data_s3_uri:-s3://$raw_bucket/input/emr_eks/happy_path/$run_id/events.csv}"
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
      "--conf" "spark.task.maxFailures=2"
      "--conf" "spark.excludeOnFailure.task.maxTaskAttemptsPerNode=1"
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
  image_pull_failure)
    expected_outcome="failed"
    missing_module="${MISSING_MODULE:-harrier_demo_missing_dependency}"
    diagnostic_signals_json="$(
      python3 - "$bad_image_uri" "$missing_module" <<'PY'
import json
import sys

image, module = sys.argv[1:]
print(json.dumps({
    "root_cause_hint": "EKS_IMAGE_PULL_FAILURE",
    "container_image": image,
    "missing_module": module,
    "log_signal": f"ImagePullBackOff while pulling {image}",
}))
PY
    )"
    application_config_json='[{"classification":"emr-containers-defaults","properties":{"job-start-timeout":"600"}}]'
    spark_submit_params+=(
      "--conf" "spark.kubernetes.container.image=$bad_image_uri"
      "--conf" "spark.executor.instances=1"
    )
    entry_args+=(
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
      "--module" "$missing_module"
    )
    ;;
  pod_pending_resource_pressure)
    expected_outcome="failed"
    local_data_file="${LOCAL_DATA_FILE:-$repo_root/sample-data/generated/emr_eks/pod_pending_resource_pressure/events-$run_id.csv}"
    data_s3_uri="${data_s3_uri:-s3://$raw_bucket/input/emr_eks/pod_pending_resource_pressure/$run_id/events.csv}"
    python3 "$repo_root/scripts/generate_data.py" --rows "$rows" --output "$local_data_file"
    aws s3 cp "$local_data_file" "$data_s3_uri" --region "$region"
    executor_instances="${PENDING_EXECUTOR_INSTANCES:-2}"
    executor_cores="${PENDING_EXECUTOR_CORES:-32}"
    executor_memory="${PENDING_EXECUTOR_MEMORY:-128g}"
    diagnostic_signals_json="$(
      python3 - "$executor_instances" "$executor_cores" "$executor_memory" <<'PY'
import json
import sys

instances, cores, memory = sys.argv[1:]
print(json.dumps({
    "root_cause_hint": "EKS_POD_PENDING",
    "pending_executor_instances": int(instances),
    "requested_executor_cores": int(cores),
    "requested_executor_memory": memory,
    "log_signal": "EKS pod pending: Unschedulable due to insufficient cpu or memory",
}))
PY
    )"
    application_config_json='[{"classification":"emr-containers-defaults","properties":{"job-start-timeout":"600"}}]'
    spark_submit_params=(
      "--conf" "spark.dynamicAllocation.enabled=false"
      "--conf" "spark.executor.instances=$executor_instances"
      "--conf" "spark.executor.cores=$executor_cores"
      "--conf" "spark.executor.memory=$executor_memory"
      "--conf" "spark.kubernetes.executor.request.cores=$executor_cores"
      "--conf" "spark.driver.cores=1"
      "--conf" "spark.driver.memory=2g"
    )
    entry_args+=(
      "--input" "$data_s3_uri"
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
    )
    ;;
  s3_access_denied)
    expected_outcome="failed"
    denied_s3_uri="${DENIED_INPUT_URI:-s3://$raw_bucket/denied/emr_eks/s3_access_denied/$run_id/secret.csv}"
    data_s3_uri="$denied_s3_uri"
    diagnostic_signals_json="$(
      python3 - "$denied_s3_uri" <<'PY'
import json
import sys

uri = sys.argv[1]
print(json.dumps({
    "root_cause_hint": "S3_ACCESS_DENIED",
    "denied_input": uri,
    "log_signal": f"AccessDenied while reading {uri}",
}))
PY
    )"
    entry_args+=(
      "--denied-input" "$denied_s3_uri"
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
    )
    ;;
  *)
    echo "EMR on EKS scenario is not implemented yet: $scenario" >&2
    echo "Supported: happy_path, executor_oom, image_pull_failure, pod_pending_resource_pressure, s3_access_denied" >&2
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
            "sparkSubmitJobDriver": {
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

python3 - "$configuration_file" "$log_uri" "$log_group" "$log_stream_prefix" "$application_config_json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
log_uri, log_group, log_stream_prefix, app_config_raw = sys.argv[2:]

try:
    app_config = json.loads(app_config_raw)
except json.JSONDecodeError:
    app_config = []

monitoring = {
    "s3MonitoringConfiguration": {
        "logUri": log_uri,
    }
}

if log_group:
    monitoring["cloudWatchMonitoringConfiguration"] = {
        "logGroupName": log_group,
        "logStreamNamePrefix": log_stream_prefix,
    }

overrides = {"monitoringConfiguration": monitoring}
if app_config:
    overrides["applicationConfiguration"] = app_config

path.write_text(json.dumps(overrides, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

job_name="harrier-demo-eks-$scenario-$run_id"
job_run_id="$(
  aws emr-containers start-job-run \
    --virtual-cluster-id "$virtual_cluster_id" \
    --client-token "$run_id" \
    --execution-role-arn "$execution_role_arn" \
    --release-label "$release_label" \
    --name "$job_name" \
    --job-driver "file://$job_driver_file" \
    --configuration-overrides "file://$configuration_file" \
    --region "$region" \
    --query id \
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
    "runtime": "emr_eks",
    "virtual_cluster_id": "$virtual_cluster_id",
    "job_run_id": "$job_run_id",
    "eks_cluster_name": "$eks_cluster_name",
    "namespace": "$namespace",
    "target": {
        "virtual_cluster_id": "$virtual_cluster_id",
        "job_run_id": "$job_run_id",
        "eks_cluster_name": "$eks_cluster_name",
        "namespace": "$namespace",
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
    "release_label": "$release_label",
    "expected_outcome": "$expected_outcome",
    "diagnostic_signals": diagnostic_signals,
    "submitted_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
}

encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
for path in (Path("$context_file"), Path("$context_dir/runs/$scenario-$run_id.json")):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(encoded, encoding="utf-8")
PY

echo "Submitted EMR on EKS job run $job_run_id for scenario $scenario"
echo "Context written to $context_file"

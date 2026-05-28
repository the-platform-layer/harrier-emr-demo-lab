#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
tf_dir="$repo_root/infra/terraform"

scenario="${SCENARIO:-${1:-happy_path}}"
run_id="${RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
rows="${ROWS:-1000}"

if [[ -n "${DEPLOY_MODE:-}" ]]; then
  deploy_mode="$DEPLOY_MODE"
else
  case "$scenario" in
    driver_oom | missing_dependency | db_connection_failure | db_lock_timeout | livy_session_failure | \
    s3_path_missing | output_path_conflict | schema_mismatch | python_worker_crash | spot_interruption)
      deploy_mode="client"
      ;;
    *)
      deploy_mode="cluster"
      ;;
  esac
fi

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
    spark_args+=(
      "--conf" "spark.dynamicAllocation.enabled=false"
      "--conf" "spark.executor.instances=$executor_instances"
      "--conf" "spark.task.maxFailures=1"
      "--conf" "spark.excludeOnFailure.enabled=false"
      "--conf" "spark.yarn.excludeDecommissioningNodes.enabled=false"
      "--conf" "spark.excludeOnFailure.task.maxTaskAttemptsPerNode=1"
      "--conf" "spark.executor.memoryOverhead=$executor_memory_overhead"
      "--executor-memory" "$executor_memory"
      "--executor-cores" "$executor_cores"
      "$job_s3_uri"
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
      "--partitions" "$partitions"
      "--allocation-mb" "$allocation_mb"
    )
    ;;
  driver_oom)
    expected_outcome="failed"
    driver_memory="${DRIVER_MEMORY:-1g}"
    driver_max_result_size="${DRIVER_MAX_RESULT_SIZE:-16m}"
    driver_rows="${DRIVER_OOM_ROWS:-25000}"
    payload_bytes="${DRIVER_OOM_PAYLOAD_BYTES:-2048}"
    diagnostic_signals_json="$(
      python3 - "$driver_rows" "$payload_bytes" "$driver_max_result_size" <<'PY'
import json
import sys

rows = int(sys.argv[1])
payload_bytes = int(sys.argv[2])
max_result = sys.argv[3]
print(json.dumps({
    "root_cause_hint": "DRIVER_OOM",
    "driver_collect_rows": rows,
    "payload_bytes_per_row": payload_bytes,
    "driver_max_result_size": max_result,
    "log_signal": "driver java.lang.OutOfMemoryError: Java heap space from collect() result pattern",
}))
PY
    )"
    spark_args+=(
      "--driver-memory" "$driver_memory"
      "--conf" "spark.driver.maxResultSize=$driver_max_result_size"
      "$job_s3_uri"
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
      "--rows" "$driver_rows"
      "--payload-bytes" "$payload_bytes"
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
    spark_args+=(
      "$job_s3_uri"
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
      "--module" "$missing_module"
    )
    ;;
  s3_access_denied)
    expected_outcome="failed"
    denied_s3_uri="${DENIED_INPUT_URI:-s3://$raw_bucket/blocked/s3_access_denied/$run_id/input.csv}"
    data_s3_uri="$denied_s3_uri"
    diagnostic_signals_json="$(
      python3 - "$denied_s3_uri" <<'PY'
import json
import sys

uri = sys.argv[1]
print(json.dumps({
    "root_cause_hint": "S3_ACCESS_DENIED",
    "denied_input_uri": uri,
    "log_signal": f"AccessDenied while reading {uri}",
}))
PY
    )"
    spark_args+=(
      "$job_s3_uri"
      "--denied-input" "$denied_s3_uri"
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
    )
    ;;
  bad_input_data)
    expected_outcome="failed"
    local_data_file="${LOCAL_DATA_FILE:-$repo_root/sample-data/generated/bad_input_data/events-$run_id.csv}"
    data_s3_uri="${data_s3_uri:-s3://$raw_bucket/input/bad_input_data/$run_id/events.csv}"
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
    spark_args+=(
      "$job_s3_uri"
      "--input" "$data_s3_uri"
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
    )
    ;;
  data_skew)
    expected_outcome="failed"
    partitions="${PARTITIONS:-24}"
    hot_rows="${HOT_ROWS:-100000}"
    cold_rows="${COLD_ROWS:-1000}"
    hot_sleep_seconds="${HOT_PARTITION_SLEEP_SECONDS:-30}"
    diagnostic_signals_json="$(
      python3 - "$hot_rows" "$cold_rows" <<'PY'
import json
import sys

hot_rows = int(sys.argv[1])
cold_rows = int(sys.argv[2])
skew_ratio = max(1, hot_rows // max(cold_rows, 1))
print(json.dumps({
    "root_cause_hint": "DATA_SKEW",
    "skew_ratio": skew_ratio,
    "log_signal": f"data skew detected; skew ratio {skew_ratio}; hot partition; long-tail task",
}))
PY
    )"
    spark_args+=(
      "$job_s3_uri"
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
      "--partitions" "$partitions"
      "--hot-rows" "$hot_rows"
      "--cold-rows" "$cold_rows"
      "--hot-partition-sleep-seconds" "$hot_sleep_seconds"
    )
    ;;
  shuffle_spill)
    expected_outcome="failed"
    shuffle_rows="${SHUFFLE_ROWS:-50000}"
    shuffle_keys="${SHUFFLE_KEYS:-64}"
    payload_bytes="${SHUFFLE_PAYLOAD_BYTES:-256}"
    shuffle_partitions="${SHUFFLE_PARTITIONS:-8}"
    diagnostic_signals_json="$(
      python3 - "$shuffle_partitions" <<'PY'
import json
import sys

partitions = int(sys.argv[1])
print(json.dumps({
    "root_cause_hint": "SHUFFLE_SPILL",
    "shuffle_partitions": partitions,
    "shuffle_spill_mb": 2048,
    "log_signal": "shuffle spill detected; memory bytes spilled and disk bytes spilled",
}))
PY
    )"
    spark_args+=(
      "--conf" "spark.sql.shuffle.partitions=$shuffle_partitions"
      "$job_s3_uri"
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
      "--rows" "$shuffle_rows"
      "--keys" "$shuffle_keys"
      "--payload-bytes" "$payload_bytes"
      "--shuffle-partitions" "$shuffle_partitions"
    )
    ;;
  kms_access_denied)
    expected_outcome="failed"
    encrypted_input="${ENCRYPTED_INPUT_URI:-s3://$raw_bucket/encrypted/kms_access_denied/$run_id/input.parquet}"
    kms_key_arn="${KMS_KEY_ARN:-arn:aws:kms:$region:111122223333:key/demo-denied}"
    data_s3_uri="$encrypted_input"
    diagnostic_signals_json="$(
      python3 - "$encrypted_input" "$kms_key_arn" <<'PY'
import json
import sys

uri, key_arn = sys.argv[1:]
print(json.dumps({
    "root_cause_hint": "KMS_ACCESS_DENIED",
    "encrypted_input_uri": uri,
    "kms_key_arn": key_arn,
    "log_signal": f"AccessDeniedException calling kms:Decrypt for encrypted S3 data {uri}",
}))
PY
    )"
    spark_args+=(
      "$job_s3_uri"
      "--encrypted-input" "$encrypted_input"
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
      "--key-arn" "$kms_key_arn"
    )
    ;;
  hdfs_full)
    expected_outcome="failed"
    local_dir="${HDFS_FULL_LOCAL_DIR:-/mnt/var/lib/hadoop/tmp/harrier-demo-$run_id}"
    diagnostic_signals_json="$(
      python3 - "$local_dir" <<'PY'
import json
import sys

local_dir = sys.argv[1]
print(json.dumps({
    "root_cause_hint": "HDFS_FULL",
    "local_dir": local_dir,
    "log_signal": f"No space left on device in HDFS; local dirs are full at {local_dir}",
}))
PY
    )"
    spark_args+=(
      "$job_s3_uri"
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
      "--local-dir" "$local_dir"
    )
    ;;
  db_connection_failure)
    expected_outcome="failed"
    jdbc_url="${JDBC_URL:-jdbc:postgresql://harrier-demo-unreachable.invalid:5432/harrier_demo}"
    diagnostic_signals_json="$(
      python3 - "$jdbc_url" <<'PY'
import json
import sys

jdbc_url = sys.argv[1]
print(json.dumps({
    "root_cause_hint": "DB_CONNECTION_FAILURE",
    "jdbc_url": jdbc_url,
    "log_signal": f"PSQLException JDBC connection refused for database host in {jdbc_url}",
}))
PY
    )"
    spark_args+=(
      "$job_s3_uri"
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
      "--jdbc-url" "$jdbc_url"
    )
    ;;
  db_lock_timeout)
    expected_outcome="failed"
    relation="${DB_LOCK_RELATION:-demo_orders}"
    lock_seconds="${DB_LOCK_SECONDS:-120}"
    diagnostic_signals_json="$(
      python3 - "$relation" "$lock_seconds" <<'PY'
import json
import sys

relation = sys.argv[1]
lock_seconds = int(sys.argv[2])
print(json.dumps({
    "root_cause_hint": "DB_LOCK_TIMEOUT",
    "relation": relation,
    "lock_seconds": lock_seconds,
    "log_signal": (
        f"PostgreSQL lock timeout waiting for lock on relation {relation}; "
        f"blocked by pid after {lock_seconds} seconds"
    ),
}))
PY
    )"
    spark_args+=(
      "$job_s3_uri"
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
      "--relation" "$relation"
      "--lock-seconds" "$lock_seconds"
    )
    ;;
  db_partition_hotspot)
    expected_outcome="failed"
    partition_column="${DB_PARTITION_COLUMN:-customer_id}"
    lower_bound="${DB_LOWER_BOUND:-1}"
    upper_bound="${DB_UPPER_BOUND:-1000000}"
    num_partitions="${DB_NUM_PARTITIONS:-1}"
    dominant_range_rows="${DB_DOMINANT_RANGE_ROWS:-250000}"
    diagnostic_signals_json="$(
      python3 - "$partition_column" "$num_partitions" "$lower_bound" "$upper_bound" <<'PY'
import json
import sys

partition_column, num_partitions, lower_bound, upper_bound = sys.argv[1:]
print(json.dumps({
    "root_cause_hint": "DB_PARTITION_HOTSPOT",
    "partition_column": partition_column,
    "num_partitions": int(num_partitions),
    "lower_bound": int(lower_bound),
    "upper_bound": int(upper_bound),
    "log_signal": (
        f"JDBC partitionColumn {partition_column} has numPartitions={num_partitions} "
        f"lowerBound={lower_bound} upperBound={upper_bound}; partition hotspot"
    ),
}))
PY
    )"
    spark_args+=(
      "$job_s3_uri"
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
      "--partition-column" "$partition_column"
      "--lower-bound" "$lower_bound"
      "--upper-bound" "$upper_bound"
      "--num-partitions" "$num_partitions"
      "--dominant-range-rows" "$dominant_range_rows"
    )
    ;;
  db_large_join_spill)
    expected_outcome="failed"
    fact_rows="${DB_FACT_ROWS:-100000}"
    dim_rows="${DB_DIM_ROWS:-20000}"
    join_keys="${DB_JOIN_KEYS:-100}"
    diagnostic_signals_json="$(
      python3 - "$fact_rows" "$dim_rows" "$join_keys" <<'PY'
import json
import sys

fact_rows, dim_rows, join_keys = (int(value) for value in sys.argv[1:])
print(json.dumps({
    "root_cause_hint": "DB_LARGE_JOIN_SPILL",
    "fact_rows": fact_rows,
    "dim_rows": dim_rows,
    "join_keys": join_keys,
    "db_plan_summary": "hash join spill to temp file; missing join-key index",
    "log_signal": "Large join caused hash join spill to temp file and work_mem pressure",
}))
PY
    )"
    spark_args+=(
      "$job_s3_uri"
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
      "--fact-rows" "$fact_rows"
      "--dim-rows" "$dim_rows"
      "--join-keys" "$join_keys"
    )
    ;;
  db_bad_sql_plan)
    expected_outcome="failed"
    query_name="${DB_QUERY_NAME:-demo_orders_customer_join}"
    diagnostic_signals_json="$(
      python3 - "$query_name" <<'PY'
import json
import sys

query_name = sys.argv[1]
print(json.dumps({
    "root_cause_hint": "DB_BAD_SQL_PLAN",
    "query_name": query_name,
    "db_plan_summary": "sequential scan and nested loop bad join order",
    "log_signal": "EXPLAIN JSON shows sequential scan and nested loop bad join order",
}))
PY
    )"
    spark_args+=(
      "$job_s3_uri"
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
      "--query-name" "$query_name"
    )
    ;;
  livy_session_failure)
    expected_outcome="failed"
    livy_session_id="${LIVY_SESSION_ID:-demo-livy-session}"
    diagnostic_signals_json="$(
      python3 - "$livy_session_id" <<'PY'
import json
import sys

session_id = sys.argv[1]
print(json.dumps({
    "root_cause_hint": "LIVY_SESSION_FAILURE",
    "session_id": session_id,
    "log_signal": f"Livy session failed while starting Spark batch for {session_id}",
}))
PY
    )"
    spark_args+=(
      "$job_s3_uri"
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
      "--session-id" "$livy_session_id"
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
  s3_path_missing)
    expected_outcome="failed"
    missing_suffix="$(python3 -c 'import uuid; print(uuid.uuid4().hex[:8])')"
    missing_input="${MISSING_INPUT:-s3://$raw_bucket/missing/$missing_suffix/nonexistent.parquet}"
    diagnostic_signals_json="$(
      python3 - "$missing_input" <<'PY'
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
    spark_args+=(
      "$job_s3_uri"
      "--missing-input" "$missing_input"
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
    )
    ;;
  output_path_conflict)
    expected_outcome="failed"
    diagnostic_signals_json="$(
      python3 - "$output_s3_uri" <<'PY'
import json
import sys

uri = sys.argv[1]
print(json.dumps({
    "root_cause_hint": "OUTPUT_PATH_CONFLICT",
    "output_uri": uri,
    "log_signal": f"path {uri} already exists; AnalysisException output path already exists",
}))
PY
    )"
    spark_args+=(
      "$job_s3_uri"
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
    )
    ;;
  schema_mismatch)
    expected_outcome="failed"
    diagnostic_signals_json="$(
      python3 - "$output_s3_uri" <<'PY'
import json
import sys

uri = sys.argv[1]
print(json.dumps({
    "root_cause_hint": "BAD_INPUT_DATA",
    "staging_uri": uri,
    "log_signal": "schema mismatch: cannot cast StringType to DoubleType; parquet type mismatch",
}))
PY
    )"
    spark_args+=(
      "$job_s3_uri"
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
    )
    ;;
  python_worker_crash)
    expected_outcome="failed"
    partitions="${PARTITIONS:-4}"
    diagnostic_signals_json="$(
      python3 - <<'PY'
import json
print(json.dumps({
    "root_cause_hint": "PYTHON_WORKER_CRASH",
    "log_signal": (
        "An exception was thrown from the Python worker. "
        "Python worker process exited unexpectedly (crashed). "
        "PythonException: unhandled exception in Python UDF executor task"
    ),
}))
PY
    )"
    spark_args+=(
      "$job_s3_uri"
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
      "--partitions" "$partitions"
    )
    ;;
  spot_interruption)
    expected_outcome="failed"
    partitions="${PARTITIONS:-4}"
    diagnostic_signals_json="$(
      python3 - <<'PY'
import json
print(json.dumps({
    "root_cause_hint": "EXECUTOR_LOST",
    "log_signal": (
        "executor lost; container killed by YARN due to node loss; "
        "remote RPC client disassociated from executor"
    ),
}))
PY
    )"
    spark_args+=(
      "--conf" "spark.task.maxFailures=2"
      "--conf" "spark.excludeOnFailure.enabled=false"
      "--conf" "spark.yarn.excludeDecommissioningNodes.enabled=false"
      "$job_s3_uri"
      "--output" "$output_s3_uri"
      "--run-id" "$run_id"
      "--partitions" "$partitions"
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
        "Type": "CUSTOM_JAR",
        "Name": f"harrier-demo-{scenario}-{run_id}",
        "ActionOnFailure": "CONTINUE",
        "Jar": "command-runner.jar",
        "Args": spark_args,
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

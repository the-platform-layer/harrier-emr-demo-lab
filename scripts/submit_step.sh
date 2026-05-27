#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
tf_dir="$repo_root/infra/terraform"

scenario="${SCENARIO:-happy_path}"
if [[ "$scenario" != "happy_path" ]]; then
  echo "submit_step.sh currently supports only the happy_path scenario" >&2
  exit 2
fi

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

local_data_file="${LOCAL_DATA_FILE:-$repo_root/sample-data/generated/happy_path/events-$run_id.csv}"
data_s3_uri="${DATA_S3_URI:-s3://$raw_bucket/input/happy_path/$run_id/events.csv}"
job_s3_uri="${JOB_S3_URI:-s3://$raw_bucket/code/happy_path/$run_id/job.py}"
output_s3_uri="${OUTPUT_S3_URI:-s3://$processed_bucket/happy_path/$run_id}"

python3 "$repo_root/scripts/generate_data.py" --rows "$rows" --output "$local_data_file"

aws s3 cp "$local_data_file" "$data_s3_uri" --region "$region"
aws s3 cp "$repo_root/spark-jobs/happy_path/job.py" "$job_s3_uri" --region "$region"

step_file="$(mktemp)"
trap 'rm -f "$step_file"' EXIT

python3 - "$step_file" "$run_id" "$deploy_mode" "$job_s3_uri" "$data_s3_uri" "$output_s3_uri" <<'PY'
import json
import sys
from pathlib import Path

step_file, run_id, deploy_mode, job_s3_uri, data_s3_uri, output_s3_uri = sys.argv[1:]
step = [
    {
        "Name": f"harrier-demo-happy-path-{run_id}",
        "ActionOnFailure": "CONTINUE",
        "HadoopJarStep": {
            "Jar": "command-runner.jar",
            "Args": [
                "spark-submit",
                "--deploy-mode",
                deploy_mode,
                job_s3_uri,
                "--input",
                data_s3_uri,
                "--output",
                output_s3_uri,
                "--run-id",
                run_id,
            ],
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
run_context_file="$context_dir/happy_path-$run_id.json"
mkdir -p "$context_dir" "$(dirname "$context_file")"

python3 - "$context_file" "$run_context_file" "$scenario" "$run_id" "$region" "$cluster_id" \
  "$deploy_mode" "$step_id" "$data_s3_uri" "$output_s3_uri" "$job_s3_uri" "$log_uri" "$submitted_at" <<'PY'
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
    submitted_at,
) = sys.argv[1:]

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
    "input_path": data_s3_uri,
    "output_path": output_s3_uri,
    "job_uri": job_s3_uri,
    "log_uri": log_uri,
    "expected_outcome": "success",
    "submitted_at": submitted_at,
}

payload = json.dumps(context, indent=2, sort_keys=True) + "\n"
Path(context_file).write_text(payload, encoding="utf-8")
Path(run_context_file).write_text(payload, encoding="utf-8")
PY

echo "Submitted happy_path step $step_id to cluster $cluster_id"
echo "Context: $context_file"

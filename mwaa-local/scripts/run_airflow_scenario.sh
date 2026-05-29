#!/usr/bin/env bash
set -euo pipefail

repo_root="${HARRIER_DEMO_REPO:-/usr/local/airflow/harrier-demo-lab}"
scenario="${SCENARIO:?SCENARIO is required}"
run_id="${RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
region="${AWS_REGION:-${AWS_DEFAULT_REGION:-ap-southeast-2}}"
context_dir="$repo_root/.harrier-demo/runs"
context_file="$context_dir/$scenario-$run_id-airflow.json"

mkdir -p "$context_dir"

export RUN_ID="$run_id"
export CONTEXT_FILE="$context_file"
export AWS_REGION="$region"
export AWS_DEFAULT_REGION="$region"

echo "Submitting Harrier demo scenario: $scenario"
echo "Run ID: $run_id"
echo "Context file: $context_file"

"$repo_root/scripts/run_scenario.sh" "$scenario"

if [[ -f "$context_file" ]]; then
  echo "Scenario context:"
  python3 -m json.tool "$context_file"

  if [[ -n "${LOGS_BUCKET:-}" ]]; then
    context_uri="s3://$LOGS_BUCKET/airflow-contexts/$scenario/$run_id/context.json"
    aws s3 cp "$context_file" "$context_uri" --region "$region"
    echo "Uploaded scenario context: $context_uri"
  fi
else
  echo "Expected context file was not created: $context_file" >&2
  exit 1
fi

step_id="$(python3 - "$context_file" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    print(json.load(handle).get("step_id", ""))
PY
)"
cluster_id="$(python3 - "$context_file" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    print(json.load(handle).get("cluster_id", ""))
PY
)"

echo "Submitted EMR step: $step_id"
echo "EMR cluster: $cluster_id"
echo "Harrier prompt seed: investigate scenario '$scenario' on cluster '$cluster_id' with step '$step_id'."

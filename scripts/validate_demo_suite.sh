#!/usr/bin/env bash
# Run the currently stable Harrier demo validation suite.
#
# Usage:
#   scripts/validate_demo_suite.sh [scenario...]
#
# Required env vars:
#   AWS_ACCOUNT_ID    12-digit AWS account ID
#   HARRIER_MCP_URL   URL of the running Harrier MCP server
#
# Optional env vars:
#   SKIP_SCENARIO_RUN  Set to 1 to validate existing context files instead of
#                      submitting fresh EMR steps
#   VALIDATE_PARALLEL  Set to 1 to validate suite scenarios in parallel.
#                      Fresh parallel runs use per-scenario context files.
#   LOG_WAIT_TIMEOUT   Max seconds to wait for EMR logs in S3 (default: 420)
#   LOG_POLL_INTERVAL  S3 log polling interval in seconds (default: 30)
#   PYTHON_BIN         Python executable to use (default: python3)
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"

default_scenarios=(
  happy_path
  executor_oom
  driver_oom
  missing_dependency
  s3_access_denied
  bad_input_data
  db_bad_sql_plan
  db_partition_hotspot
  kms_access_denied
  data_skew
  shuffle_spill
  hdfs_full
  db_connection_failure
  db_lock_timeout
  db_large_join_spill
  glue_metastore_error
  livy_session_failure
  s3_path_missing
  output_path_conflict
  schema_mismatch
  python_worker_crash
  unknown_failure
  spot_interruption
)

if [[ $# -gt 0 ]]; then
  scenarios=("$@")
else
  scenarios=("${default_scenarios[@]}")
fi

if [[ -z "${AWS_ACCOUNT_ID:-}" ]]; then
  echo "AWS_ACCOUNT_ID is required" >&2
  exit 2
fi

if [[ -z "${HARRIER_MCP_URL:-}" ]]; then
  echo "HARRIER_MCP_URL is required" >&2
  exit 2
fi

overall=0
echo "Running Harrier demo validation suite: ${scenarios[*]}"

run_one() {
  local scenario="$1"
  local -a args

  echo
  echo "=== ${scenario} ==="

  args=("$scenario")
  if [[ "${SKIP_SCENARIO_RUN:-0}" == "1" ]]; then
    context_file="$(
      find "$repo_root/.harrier-demo/runs" \
        -maxdepth 1 \
        -type f \
        -name "${scenario}-*.json" \
        ! -name "*-exported.json" \
        2>/dev/null \
      | sort \
      | tail -n 1
    )"

    if [[ -z "$context_file" ]]; then
      echo "No existing context file found for ${scenario}" >&2
      return 1
    fi

    args+=("--context-file" "$context_file")
  fi

  "$repo_root/scripts/validate_scenario.sh" "${args[@]}"
}

if [[ "${VALIDATE_PARALLEL:-0}" == "1" ]]; then
  tmp_dir="${TMPDIR:-/tmp}/harrier-validate-suite-$$"
  mkdir -p "$tmp_dir"

  for scenario in "${scenarios[@]}"; do
    (
      set +e
      run_one "$scenario" > "$tmp_dir/${scenario}.log" 2>&1
      printf '%s\n' "$?" > "$tmp_dir/${scenario}.rc"
    ) &
  done
  wait

  for scenario in "${scenarios[@]}"; do
    cat "$tmp_dir/${scenario}.log"
    if [[ "$(cat "$tmp_dir/${scenario}.rc")" -ne 0 ]]; then
      overall=1
    fi
  done

  rm -rf "$tmp_dir"
else
  for scenario in "${scenarios[@]}"; do
    if ! run_one "$scenario"; then
      overall=1
    fi
  done
fi

echo
if [[ "$overall" -eq 0 ]]; then
  echo "Harrier demo validation suite passed."
else
  echo "Harrier demo validation suite failed." >&2
fi

exit "$overall"

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
for scenario in "${scenarios[@]}"; do
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
      overall=1
      continue
    fi

    args+=("--context-file" "$context_file")
  fi

  if ! "$repo_root/scripts/validate_scenario.sh" "${args[@]}"; then
    overall=1
  fi
done

echo
if [[ "$overall" -eq 0 ]]; then
  echo "Harrier demo validation suite passed."
else
  echo "Harrier demo validation suite failed." >&2
fi

exit "$overall"

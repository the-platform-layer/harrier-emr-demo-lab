#!/usr/bin/env bash
# Scenario validation harness for Harrier EMR Demo Lab.
#
# Usage:
#   scripts/validate_scenario.sh <scenario> [extra args passed to validate.py]
#
# Required env vars:
#   HARRIER_MCP_URL   URL of the running Harrier MCP server
#                     (default: http://localhost:8000/mcp)
#   AWS_ACCOUNT_ID    12-digit AWS account ID
#
# Optional env vars:
#   SKIP_SCENARIO_RUN  Set to 1 to skip job submission and use existing context
#   CLUSTER_ID         Override cluster_id from context
#   AWS_REGION         Override region from context
#   LOG_WAIT_TIMEOUT   Max seconds to wait for EMR logs in S3 (default: 420)
#   LOG_POLL_INTERVAL  S3 log polling interval in seconds (default: 30)
#   NO_LOG_WAIT        Set to 1 to skip the EMR S3 log wait
#   PYTHON_BIN         Python executable to use (default: python3)
#
# Examples:
#   # Run the executor_oom scenario end-to-end and validate Harrier's finding:
#   AWS_ACCOUNT_ID=123456789012 \
#   HARRIER_MCP_URL=http://localhost:8000/mcp \
#   scripts/validate_scenario.sh executor_oom
#
#   # Validate against an existing context file (no AWS step submission):
#   SKIP_SCENARIO_RUN=1 \
#   AWS_ACCOUNT_ID=123456789012 \
#   HARRIER_MCP_URL=http://localhost:8000/mcp \
#   scripts/validate_scenario.sh executor_oom \
#     --context-file .harrier-demo/runs/executor_oom-20260528T120000Z.json
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
python_bin="${PYTHON_BIN:-python3}"

scenario="${1:-}"
if [[ $# -gt 0 ]]; then
  shift
fi

exec "$python_bin" "$repo_root/validation/validate.py" \
  ${scenario:+--scenario "$scenario"} \
  "$@"

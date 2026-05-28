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

scenario="${1:-}"
if [[ $# -gt 0 ]]; then
  shift
fi

exec /usr/local/bin/python3.10 "$repo_root/validation/validate.py" \
  ${scenario:+--scenario "$scenario"} \
  "$@"

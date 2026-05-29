#!/usr/bin/env bash
# Run demo scenarios end-to-end and validate each one against Harrier MCP.
#
# Usage:
#   bash scripts/run_all_validation.sh [OPTIONS] [scenario ...]
#
# Options:
#   --mcp-url URL         Harrier MCP URL (env: HARRIER_MCP_URL)
#   --account-id ID       12-digit AWS account ID (env: AWS_ACCOUNT_ID)
#   --log-wait SECONDS    Wait after step completion before validating
#                         (env: LOG_WAIT_SECONDS, default: 60 for client-mode,
#                          300 for cluster-mode)
#   --dry-run             Print plan without submitting any steps
#
# If no scenarios are given, all failed-step scenarios are run in order.
#
# Scenarios that run as an actual EMR step and validate the failed result:
#   executor_oom  missing_dependency  s3_access_denied  bad_input_data
#   hdfs_full  kms_access_denied  driver_oom  shuffle_spill  data_skew
#   livy_session_failure  db_connection_failure  glue_metastore_error
#   s3_path_missing  output_path_conflict  schema_mismatch
#   python_worker_crash  unknown_failure  spot_interruption
#
# Running-job scenarios (require Harrier to be called mid-execution, not automated here):
#   long_running_data_delay  long_running_resource_delay  long_running_db_delay

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONTEXT_FILE="$REPO_ROOT/.harrier-demo/last-context.json"

MCP_URL="${HARRIER_MCP_URL:-http://devops-agent-demo-demo-s4-alb-1760538847.ap-southeast-2.elb.amazonaws.com:8080/mcp}"
ACCOUNT_ID="${AWS_ACCOUNT_ID:-633867805930}"
CLIENT_LOG_WAIT="${LOG_WAIT_SECONDS:-60}"
CLUSTER_LOG_WAIT="${CLUSTER_LOG_WAIT_SECONDS:-300}"
DRY_RUN=0

# Canonical order for the full suite
ALL_SCENARIOS=(
  executor_oom
  missing_dependency
  s3_access_denied
  bad_input_data
  s3_path_missing
  output_path_conflict
  schema_mismatch
  python_worker_crash
  unknown_failure
  spot_interruption
  driver_oom
  shuffle_spill
  data_skew
  hdfs_full
  kms_access_denied
  livy_session_failure
  db_connection_failure
  glue_metastore_error
)

# Parse arguments
SCENARIOS_TO_RUN=()
while (($# > 0)); do
  case "$1" in
    --mcp-url)    MCP_URL="$2";    shift 2 ;;
    --account-id) ACCOUNT_ID="$2"; shift 2 ;;
    --log-wait)   CLIENT_LOG_WAIT="$2"; shift 2 ;;
    --dry-run)    DRY_RUN=1;       shift ;;
    -*)           echo "Unknown option: $1" >&2; exit 2 ;;
    *)            SCENARIOS_TO_RUN+=("$1"); shift ;;
  esac
done

[[ ${#SCENARIOS_TO_RUN[@]} -eq 0 ]] && SCENARIOS_TO_RUN=("${ALL_SCENARIOS[@]}")

# ─── Helpers ──────────────────────────────────────────────────────────────────

scenario_ctx_field() {
  local ctx_file="$1" field="$2"
  python3 -c "
import json, sys
data = json.load(open('$ctx_file'))
print(data.get('$field') or '')
" 2>/dev/null || true
}

wait_for_step() {
  local cluster_id="$1" step_id="$2" region="$3"
  local state
  while true; do
    state="$(aws emr describe-step \
      --cluster-id "$cluster_id" \
      --step-id    "$step_id" \
      --region     "$region" \
      --query 'Step.Status.State' \
      --output text 2>/dev/null)"
    printf "    %s\n" "$state"
    case "$state" in
      COMPLETED|FAILED|CANCELLED|INTERRUPTED) return 0 ;;
    esac
    sleep 20
  done
}

# ─── Per-scenario runner ───────────────────────────────────────────────────────

PASS=()
FAIL=()
SKIP=()
ERRORS=()

run_scenario() {
  local scenario="$1"
  # Use a scenario-specific context file to prevent contamination from concurrent runs.
  local ctx_file="$REPO_ROOT/.harrier-demo/runs/validation-${scenario}.json"

  printf "\n"
  printf "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
  printf " SCENARIO: %s\n" "$scenario"
  printf "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

  if [[ $DRY_RUN -eq 1 ]]; then
    echo "  [DRY-RUN] would submit $scenario"
    return
  fi

  # 1. Submit — write context to a scenario-specific file
  printf "[1/4] Submitting step...\n"
  if ! SCENARIO="$scenario" CONTEXT_FILE="$ctx_file" bash "$SCRIPT_DIR/submit_step.sh" 2>&1; then
    echo "  SKIP: submit_step.sh failed — scenario may not be implemented yet"
    SKIP+=("$scenario")
    return
  fi

  # 2. Wait for step — read step_id from the scenario-specific file
  local step_id cluster_id region
  step_id="$(scenario_ctx_field "$ctx_file" step_id)"
  cluster_id="$(scenario_ctx_field "$ctx_file" cluster_id)"
  region="$(scenario_ctx_field "$ctx_file" region)"

  printf "[2/4] Waiting for step %s...\n" "$step_id"
  wait_for_step "$cluster_id" "$step_id" "$region"

  # 3. Export context — enrich the scenario-specific file with live EMR data
  printf "[3/4] Exporting investigation context...\n"
  CONTEXT_FILE="$ctx_file" bash "$SCRIPT_DIR/export_investigation_context.sh" 2>&1 || true

  # 4. Wait for log aggregation
  local deploy_mode wait_s
  deploy_mode="$(scenario_ctx_field "$ctx_file" deploy_mode)"
  if [[ "$deploy_mode" == "cluster" ]]; then
    wait_s="$CLUSTER_LOG_WAIT"
  else
    wait_s="$CLIENT_LOG_WAIT"
  fi
  printf "[4/4] Waiting %ss for log aggregation (deploy_mode=%s)...\n" "$wait_s" "$deploy_mode"
  sleep "$wait_s"

  # 5. Validate — use the scenario-specific context file
  if python3 "$REPO_ROOT/validation/validate.py" \
      --scenario    "$scenario" \
      --context-file "$ctx_file" \
      --skip-run \
      --mcp-url     "$MCP_URL" \
      --account-id  "$ACCOUNT_ID" 2>&1; then
    PASS+=("$scenario")
  else
    FAIL+=("$scenario")
  fi
}

# ─── Main ─────────────────────────────────────────────────────────────────────

printf "Harrier EMR Demo Lab — Full Validation Suite\n"
printf "  MCP URL    : %s\n" "$MCP_URL"
printf "  Account ID : %s\n" "$ACCOUNT_ID"
printf "  Scenarios  : %s\n" "${SCENARIOS_TO_RUN[*]}"
printf "  Log wait   : client=%ss cluster=%ss\n" "$CLIENT_LOG_WAIT" "$CLUSTER_LOG_WAIT"
[[ $DRY_RUN -eq 1 ]] && printf "  Mode       : DRY-RUN (no steps submitted)\n"

for scenario in "${SCENARIOS_TO_RUN[@]}"; do
  run_scenario "$scenario"
done

# ─── Summary ──────────────────────────────────────────────────────────────────

printf "\n"
printf "═══════════════════════════════════════════════════════════\n"
printf " VALIDATION SUMMARY\n"
printf "═══════════════════════════════════════════════════════════\n"
printf " PASS (%d): %s\n" "${#PASS[@]}"  "${PASS[*]:-—}"
printf " FAIL (%d): %s\n" "${#FAIL[@]}"  "${FAIL[*]:-—}"
printf " SKIP (%d): %s\n" "${#SKIP[@]}"  "${SKIP[*]:-—}"
printf "═══════════════════════════════════════════════════════════\n"

[[ ${#FAIL[@]} -gt 0 ]] && exit 1 || exit 0

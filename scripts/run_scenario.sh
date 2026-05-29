#!/usr/bin/env bash
set -euo pipefail

scenario="${1:-}"
if [[ -z "$scenario" ]]; then
  echo "usage: $0 <scenario>" >&2
  exit 2
fi

repo_root="$(cd "$(dirname "$0")/.." && pwd)"

case "$scenario" in
  happy_path | executor_oom | driver_oom | missing_dependency | s3_access_denied | bad_input_data | \
    data_skew | shuffle_spill | kms_access_denied | hdfs_full | db_connection_failure | \
    db_lock_timeout | db_partition_hotspot | db_large_join_spill | db_bad_sql_plan | \
    s3_path_missing | output_path_conflict | schema_mismatch | python_worker_crash | \
    unknown_failure | spot_interruption | \
    livy_session_failure | \
    long_running_data_delay | long_running_resource_delay | long_running_db_delay)
    SCENARIO="$scenario" "$repo_root/scripts/submit_step.sh"
    ;;
  *)
    echo "scenario is not implemented yet: $scenario" >&2
    exit 2
    ;;
esac

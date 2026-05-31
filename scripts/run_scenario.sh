#!/usr/bin/env bash
set -euo pipefail

scenario="${1:-}"
if [[ -z "$scenario" ]]; then
  echo "usage: $0 <scenario>" >&2
  exit 2
fi

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
runtime="${RUNTIME:-${HARRIER_RUNTIME:-${SCENARIO_RUNTIME:-emr_ec2}}}"

case "$runtime" in
  emr_ec2 | ec2)
    case "$scenario" in
      happy_path | executor_oom | driver_oom | missing_dependency | s3_access_denied | bad_input_data | \
        data_skew | shuffle_spill | kms_access_denied | hdfs_full | db_connection_failure | \
        db_lock_timeout | db_partition_hotspot | db_large_join_spill | db_bad_sql_plan | \
        s3_path_missing | output_path_conflict | schema_mismatch | python_worker_crash | \
        unknown_failure | glue_metastore_error | spot_interruption | \
        livy_session_failure | \
        long_running_data_delay | long_running_resource_delay | long_running_db_delay)
        SCENARIO="$scenario" "$repo_root/scripts/submit_step.sh"
        ;;
      *)
        echo "scenario is not implemented yet for EMR on EC2: $scenario" >&2
        exit 2
        ;;
    esac
    ;;
  emr_serverless | serverless)
    case "$scenario" in
      happy_path | executor_oom | missing_dependency | s3_path_missing | bad_input_data)
        RUNTIME="emr_serverless" SCENARIO="$scenario" "$repo_root/scripts/submit_serverless_job.sh"
        ;;
      *)
        echo "scenario is not implemented yet for EMR Serverless: $scenario" >&2
        echo "Supported: happy_path, executor_oom, missing_dependency, s3_path_missing, bad_input_data" >&2
        exit 2
        ;;
    esac
    ;;
  emr_eks | eks)
    case "$scenario" in
      happy_path | executor_oom | image_pull_failure | pod_pending_resource_pressure | s3_access_denied)
        RUNTIME="emr_eks" SCENARIO="$scenario" "$repo_root/scripts/submit_eks_job.sh"
        ;;
      *)
        echo "scenario is not implemented yet for EMR on EKS: $scenario" >&2
        echo "Supported: happy_path, executor_oom, image_pull_failure, pod_pending_resource_pressure, s3_access_denied" >&2
        exit 2
        ;;
    esac
    ;;
  *)
    echo "runtime is not implemented yet: $runtime" >&2
    echo "Supported runtimes: emr_ec2, emr_serverless, emr_eks" >&2
    exit 2
    ;;
esac

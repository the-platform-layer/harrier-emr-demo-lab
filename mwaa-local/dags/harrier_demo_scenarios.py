from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.models.param import Param
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator


SCENARIOS = [
    "happy_path",
    "executor_oom",
    "driver_oom",
    "missing_dependency",
    "s3_access_denied",
    "bad_input_data",
    "data_skew",
    "shuffle_spill",
    "kms_access_denied",
    "hdfs_full",
    "db_connection_failure",
    "db_lock_timeout",
    "db_partition_hotspot",
    "db_large_join_spill",
    "db_bad_sql_plan",
    "s3_path_missing",
    "output_path_conflict",
    "schema_mismatch",
    "python_worker_crash",
    "unknown_failure",
    "glue_metastore_error",
    "spot_interruption",
    "livy_session_failure",
    "long_running_data_delay",
    "long_running_resource_delay",
    "long_running_db_delay",
]

SMOKE_SUITE = [
    "happy_path",
    "executor_oom",
    "driver_oom",
    "db_bad_sql_plan",
    "db_partition_hotspot",
]


def _scenario_command(default_scenario: str | None = None) -> str:
    scenario_expr = default_scenario or "{{ dag_run.conf.get('scenario', params.scenario) }}"
    return f"""
set -euo pipefail
export SCENARIO="{scenario_expr}"
export RUN_ID="{{{{ dag_run.conf.get('run_id', ts_nodash) }}}}"
export ROWS="{{{{ dag_run.conf.get('rows', params.rows) }}}}"
deploy_mode="{{{{ dag_run.conf.get('deploy_mode', params.deploy_mode) }}}}"
if [[ "$deploy_mode" != "auto" ]]; then
  export DEPLOY_MODE="$deploy_mode"
fi
/usr/local/airflow/harrier-demo-lab/mwaa-local/scripts/run_airflow_scenario.sh
"""


default_args = {
    "owner": "harrier-demo",
    "retries": 0,
}


with DAG(
    dag_id="harrier_demo_run_scenario",
    description="Submit one Harrier EMR demo scenario through the MWAA-compatible runner.",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["harrier", "emr", "demo"],
    params={
        "scenario": Param("happy_path", enum=SCENARIOS),
        "deploy_mode": Param("auto", enum=["auto", "client", "cluster"]),
        "rows": Param(1000, type="integer", minimum=1),
    },
) as run_scenario_dag:
    start = EmptyOperator(task_id="start")
    submit = BashOperator(
        task_id="submit_emr_demo_scenario",
        bash_command=_scenario_command(),
    )
    done = EmptyOperator(task_id="done")

    start >> submit >> done


with DAG(
    dag_id="harrier_demo_smoke_suite",
    description="Submit a small sequential Harrier EMR scenario suite.",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["harrier", "emr", "demo", "suite"],
    params={
        "deploy_mode": Param("auto", enum=["auto", "client", "cluster"]),
        "rows": Param(1000, type="integer", minimum=1),
    },
) as smoke_suite_dag:
    previous = EmptyOperator(task_id="start")
    for scenario in SMOKE_SUITE:
        task = BashOperator(
            task_id=f"submit_{scenario}",
            bash_command=_scenario_command(scenario),
        )
        previous >> task
        previous = task

    previous >> EmptyOperator(task_id="done")

import ast
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_mwaa_dag_defines_single_scenario_and_smoke_suite():
    dag_file = ROOT / "mwaa-local" / "dags" / "harrier_demo_scenarios.py"
    source = dag_file.read_text(encoding="utf-8")

    ast.parse(source)

    assert "harrier_demo_run_scenario" in source
    assert "harrier_demo_smoke_suite" in source
    assert "executor_oom" in source
    assert "db_bad_sql_plan" in source
    assert "db_partition_hotspot" in source


def test_mwaa_scripts_are_shell_syntax_valid():
    scripts = [
        ROOT / "scripts" / "build_mwaa_local_runner_image.sh",
        ROOT / "scripts" / "deploy_mwaa_local_runner.sh",
        ROOT / "mwaa-local" / "scripts" / "run_airflow_scenario.sh",
        ROOT / "mwaa-local" / "startup_script" / "startup.sh",
    ]

    for script in scripts:
        subprocess.run(["bash", "-n", str(script)], check=True)


def test_mwaa_build_uses_aws_local_runner_source():
    build_script = (ROOT / "scripts" / "build_mwaa_local_runner_image.sh").read_text(
        encoding="utf-8"
    )

    assert "https://github.com/aws/aws-mwaa-local-runner.git" in build_script
    assert "v2.10.3" in build_script
    assert "docker build --rm --compress" in build_script
    assert "--network \"$docker_build_network\"" in build_script


def test_mwaa_terraform_defines_ecs_and_ecr_resources():
    terraform = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [
            ROOT / "infra" / "terraform" / "mwaa-ecr.tf",
            ROOT / "infra" / "terraform" / "mwaa-ecs.tf",
            ROOT / "infra" / "terraform" / "mwaa-iam.tf",
        ]
    )

    assert 'resource "aws_ecr_repository" "mwaa_local_runner"' in terraform
    assert 'resource "aws_ecs_service" "mwaa"' in terraform
    assert 'resource "aws_lb" "mwaa"' in terraform
    assert 'resource "aws_iam_role" "mwaa_task"' in terraform
    assert "aws_emr_cluster.demo.id" in terraform
    assert "AIRFLOW__API__AUTH_BACKENDS" in terraform
    assert "airflow.api.auth.backend.basic_auth" in terraform

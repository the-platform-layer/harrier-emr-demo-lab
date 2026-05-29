# MWAA Local Runner On ECS

The demo lab can run its scenario orchestration through AWS's MWAA-compatible local runner container on ECS Fargate.

This is intentionally a demo orchestration layer:

- Image source: `aws/aws-mwaa-local-runner`, default branch `v2.10.3`.
- Runtime: Apache Airflow in a MWAA-like container.
- Executor: `SequentialExecutor` in one Fargate task to keep the demo small.
- Scenario execution: DAGs call the existing `scripts/run_scenario.sh` path, so Airflow and shell validation use the same scenario runner.

## Deploy

```bash
scripts/deploy_mwaa_local_runner.sh
```

The helper:

1. Creates the MWAA local runner ECR repository.
2. Clones AWS's local runner source into `.harrier-demo/aws-mwaa-local-runner`.
3. Builds the AWS MWAA local runner base image.
4. Builds the Harrier demo overlay image.
5. Pushes the image to ECR.
6. Applies Terraform with `mwaa_desired_count=1`.

By default the deploy helper tries to restrict the Airflow UI security group to your current public IP. To override it:

```bash
MWAA_WEB_ALLOWED_CIDRS='["203.0.113.10/32"]' scripts/deploy_mwaa_local_runner.sh
```

## Access

After deploy:

```bash
terraform -chdir=infra/terraform output mwaa_airflow_url
terraform -chdir=infra/terraform output mwaa_admin_password_secret_arn
```

Username is `admin`. The password is stored in Secrets Manager.

The Airflow REST API is enabled for Basic Auth so validation scripts can use the same credentials:

```bash
URL=$(terraform -chdir=infra/terraform output -raw mwaa_airflow_url)
PASSWORD=$(aws secretsmanager get-secret-value \
  --secret-id harrier-demo/mwaa/admin-password \
  --region ap-southeast-2 \
  --query SecretString \
  --output text)

curl -u "admin:${PASSWORD}" "${URL}/api/v1/dags?limit=100"
```

## DAGs

`harrier_demo_run_scenario`

- Manual DAG.
- Trigger with a selected `scenario`.
- Optional params:
  - `deploy_mode`: `auto`, `client`, or `cluster`
  - `rows`: sample row count for data-generating scenarios

`harrier_demo_smoke_suite`

- Manual DAG.
- Submits a small sequential suite:
  - `happy_path`
  - `executor_oom`
  - `driver_oom`
  - `db_bad_sql_plan`
  - `db_partition_hotspot`

## Context Artifacts

Each Airflow run writes scenario context in the container and uploads a copy to:

```text
s3://<logs-bucket>/airflow-contexts/<scenario>/<run-id>/context.json
```

The context contains the EMR cluster ID, step ID, deploy mode, log URI, and diagnostic hints needed by Harrier.

## Online Verification

After ECS is stable, verify the live runner before a demo:

```bash
aws ecs wait services-stable \
  --cluster harrier-demo-mwaa-local-runner \
  --services harrier-demo-mwaa-local-runner \
  --region ap-southeast-2

curl "${URL}/health"
curl -u "admin:${PASSWORD}" "${URL}/api/v1/dags?limit=100"
```

To submit a lightweight online smoke run:

```bash
RUN_ID="online-happy-path-$(date -u +%Y%m%dT%H%M%SZ)"
curl -u "admin:${PASSWORD}" \
  -H "Content-Type: application/json" \
  -X POST "${URL}/api/v1/dags/harrier_demo_run_scenario/dagRuns" \
  --data "{\"dag_run_id\":\"${RUN_ID}\",\"conf\":{\"scenario\":\"happy_path\",\"deploy_mode\":\"cluster\",\"rows\":1000,\"run_id\":\"${RUN_ID}\"}}"
```

Then inspect:

```bash
aws s3 cp "s3://harrier-demo-logs-8193211c/airflow-contexts/happy_path/${RUN_ID}/context.json" -
```

## Cost Controls

`mwaa_desired_count` defaults to `0` so baseline Terraform can create definitions before an image exists. The deploy helper sets it to `1`.

To pause the Airflow demo runner without destroying all resources:

```bash
terraform -chdir=infra/terraform apply -var mwaa_desired_count=0
```

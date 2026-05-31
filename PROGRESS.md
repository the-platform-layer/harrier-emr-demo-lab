# Harrier EMR Demo Lab Progress

Use this file as the handoff point between chats, sessions, and contributors.

Detailed implementation checklists live in [TASKS.md](TASKS.md).

## Current State

Status: Slice 31 implemented, pending live EMR on EKS validation.

Remote: https://github.com/the-platform-layer/harrier-emr-demo-lab

Last verified:

- Terraform Slice 2 baseline validates.
- Terraform can produce a no-refresh plan for 39 resources.
- Demo EMR on EC2 baseline infrastructure is defined.
- Happy path Spark job is implemented.
- Happy path data generation and EMR step submission helpers are implemented.
- Investigation context export is implemented with deploy mode, job state, and best-effort YARN application ID extraction.
- Long-running data, resource, and DB delay scenario jobs are implemented.
- Slice 10 batch 1 failure scenarios are implemented and wired into the runner.
- Slice 14 advanced Spark/IAM/storage/DB/Livy scenarios are implemented and wired into the runner.
- Local verification passed; the job has not been submitted to a live EMR cluster in this session.
- Scenario configs and expected findings exist for Slice 10 and Slice 14.
- Scenario validation harness is implemented: `validation/` Python package with MCP HTTP client, comparator, report writer, and CLI; `scripts/validate_scenario.sh` shell wrapper; 109 unit tests all pass.
- AWS MWAA-compatible local runner orchestration is implemented for ECS Fargate: DAGs, image build/deploy scripts, ECR/ECS/ALB/IAM Terraform, and docs.
- EMR Serverless demo support is implemented: Terraform application and job role, Serverless scenario submitter, runtime-aware context export, validation harness support, scenario configs, and docs for `happy_path`, `executor_oom`, `missing_dependency`, `s3_path_missing`, and `bad_input_data`.
- EMR on EKS demo support is implemented for an existing EKS cluster: prerequisite/setup docs and helper, optional Terraform virtual cluster registration, EKS scenario submitter, runtime-aware context export, validation harness support, cleanup, scenario configs, and expected findings for `happy_path`, `executor_oom`, `image_pull_failure`, `pod_pending_resource_pressure`, and `s3_access_denied`.
- Repo contains no production MCP server implementation or MCP deployment infrastructure.

## Decisions

- This repo owns all demo resources and scenario automation.
- Drop 1 demo targets Amazon EMR on EC2.
- Slice 30 validates the same Spark failure signatures under EMR Serverless; expected findings are reused while the runtime target and log layout change.
- Slice 31 uses an existing EKS cluster instead of creating one; the demo lab registers a namespace as an EMR on EKS virtual cluster and keeps Kubernetes access read-only for Harrier diagnostics.
- Demo resources must be disposable and clearly tagged.
- RDS resources stay disabled by default; DB scenarios use safe simulations unless a live DB path is explicitly enabled.
- Demo scripts can invoke an already-running Harrier MCP endpoint, but they do not host or deploy Harrier.
- Long-running jobs are first-class demo targets; they should produce evidence before the Spark step fails.

## Repo Boundary

This repo owns:

- Demo EMR infrastructure
- Demo RDS/Glue/CloudWatch resources
- Demo IAM roles and policies
- Demo Spark jobs
- Demo sample data
- Demo scenario scripts
- Demo alarms
- Expected findings
- Scenario validation harness
- Demo cleanup and cost controls
- Demo documentation

This repo does not own:

- Production Harrier MCP server implementation
- MCP deployment infrastructure
- AWS DevOps Agent MCP registration assets

## Build Plan

| Slice | Status | Owner Repo | Notes |
| --- | --- | --- | --- |
| 0. Bootstrap repos | Done | both | Initial private repos created under `the-platform-layer`. |
| 2. Demo EMR baseline infra | Done | harrier-emr-demo-lab | VPC, S3, EMR, IAM, logging, lifecycle, alarms, and docs added. |
| 3. Happy path Spark job | Implemented | harrier-emr-demo-lab | Generate data, submit EMR step, export investigation context. Needs live EMR run. |
| 10. Demo scenarios batch 1 | Implemented | harrier-emr-demo-lab | `executor_oom`, `driver_oom`, `missing_dependency`, `s3_access_denied`, `bad_input_data`; live EMR validation still needed. |
| 14. Demo scenarios batch 2 | Implemented | harrier-emr-demo-lab | Advanced Spark/IAM/storage/DB/Livy and long-running delay scenarios; live EMR validation still needed. |
| 19. Scenario validation harness | Done | harrier-emr-demo-lab | `validation/` package: MCP client, comparator, report writer, CLI; `scripts/validate_scenario.sh` wrapper; 83 unit tests pass; no live AWS calls required for tests. |
| 20. MWAA local runner on ECS | Implemented | harrier-emr-demo-lab | AWS MWAA local-runner image source, Harrier DAG overlay, ECS Fargate service, ALB, ECR, IAM, and deploy helper. |
| 30. Demo lab Serverless scenarios | Implemented | harrier-emr-demo-lab | EMR Serverless app Terraform, job role, submitter, five scenario configs, runtime-aware context export, and validation harness support. Live Serverless validation still pending. |
| 31. Demo lab EKS scenarios | Implemented | harrier-emr-demo-lab | Existing-EKS prerequisite helper, virtual cluster registration, EMR Containers submitter, five scenario configs, EKS expected findings, cleanup, docs, and validation harness support. Live EKS validation still pending. |

## Next Session Start Here

Recommended next task:

1. Deploy the demo baseline in a demo AWS account if not already running.
2. Run `./scripts/run_scenario.sh happy_path`.
3. Confirm processed S3 output and EMR logs.
4. Export context with `./scripts/export_investigation_context.sh`.
5. Start the Harrier MCP server locally or on ECS Fargate.
6. Run the validation harness end-to-end against a live scenario:
   ```bash
   AWS_ACCOUNT_ID=123456789012 \
   HARRIER_MCP_URL=http://localhost:8000/mcp \
   scripts/validate_scenario.sh executor_oom
   ```
7. Check the validation report in `.harrier-demo/validation/`.
8. Run one EMR Serverless validation:
   ```bash
   AWS_ACCOUNT_ID=123456789012 \
   RUNTIME=emr_serverless \
   scripts/validate_scenario.sh executor_oom
   ```
9. Prepare an EMR on EKS namespace and run one EKS validation:
   ```bash
   EMR_EKS_CLUSTER_NAME=analytics-dev \
   EMR_EKS_JOB_ROLE_ARN=arn:aws:iam::123456789012:role/harrier-demo-emr-eks-job \
   scripts/setup_eks_virtual_cluster.sh

   AWS_ACCOUNT_ID=123456789012 \
   RUNTIME=emr_eks \
   scripts/validate_scenario.sh image_pull_failure
   ```
10. Deploy MWAA local runner orchestration:
   ```bash
   ./scripts/deploy_mwaa_local_runner.sh
   ```

## Open Questions

- Confirm allowed instance types and max runtime for demo clusters.
- Decide whether default instance types should remain `m5.xlarge` before first real deploy.

## Useful Commands

```bash
cd /Users/pinakimukherjee/Documents/Workspace/harrier-emr-demo-lab
python3 -m compileall scripts spark-jobs db
find . -maxdepth 3 -type f | sort
cd infra/terraform && terraform validate
cd infra/terraform && terraform plan -refresh=false
RUNTIME=emr_serverless ./scripts/run_scenario.sh executor_oom
RUNTIME=emr_eks ./scripts/run_scenario.sh image_pull_failure
```

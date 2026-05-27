# Harrier EMR Demo Lab Progress

Use this file as the handoff point between chats, sessions, and contributors.

Detailed implementation checklists live in [TASKS.md](TASKS.md).

## Current State

Status: Slice 3 implemented; live AWS verification pending.

Remote: https://github.com/the-platform-layer/harrier-emr-demo-lab

Last verified:

- Terraform Slice 2 baseline validates.
- Terraform can produce a no-refresh plan for 39 resources.
- Demo EMR on EC2 baseline infrastructure is defined.
- Happy path Spark job is implemented.
- Happy path data generation and EMR step submission helpers are implemented.
- Investigation context export is implemented with deploy mode, job state, and best-effort YARN application ID extraction.
- Long-running data, resource, and DB delay scenario jobs are implemented.
- Local verification passed; the job has not been submitted to a live EMR cluster in this session.
- Scenario folder structure and expected findings placeholders exist.
- Repo contains no production MCP server implementation or MCP deployment infrastructure.

## Decisions

- This repo owns all demo resources and scenario automation.
- Drop 1 demo targets Amazon EMR on EC2.
- Demo resources must be disposable and clearly tagged.
- RDS resources stay disabled by default until DB scenarios are implemented.
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
| 10. Demo scenarios batch 1 | Not started | harrier-emr-demo-lab | `executor_oom`, `driver_oom`, `missing_dependency`, `s3_access_denied`, `bad_input_data`. |
| 14. Demo scenarios batch 2 | Not started | harrier-emr-demo-lab | Advanced Spark/IAM/DB/Livy/storage and long-running delay scenarios. |
| 19. Scenario validation harness | Started | harrier-emr-demo-lab | Placeholder script exists. |

## Next Session Start Here

Recommended next task:

1. Deploy the demo baseline in a demo AWS account if not already running.
2. Run `./scripts/run_scenario.sh happy_path`.
3. Confirm processed S3 output and EMR logs.
4. Export context with `./scripts/export_investigation_context.sh`.
5. Start Slice 10 with the first controlled failure scenario.

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
```

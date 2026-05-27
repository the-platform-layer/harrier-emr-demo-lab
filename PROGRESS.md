# Harrier EMR Demo Lab Progress

Use this file as the handoff point between chats, sessions, and contributors.

## Current State

Status: Slice 0 scaffold complete.

Remote: https://github.com/the-platform-layer/harrier-emr-demo-lab

Last verified:

- Python placeholder files compile.
- Scenario folder structure exists.
- Expected findings placeholders exist.
- Repo contains no production MCP server implementation or MCP deployment infrastructure.

## Decisions

- This repo owns all demo resources and scenario automation.
- Drop 1 demo targets Amazon EMR on EC2.
- Demo resources must be disposable and clearly tagged.
- RDS resources stay disabled by default until DB scenarios are implemented.
- Demo scripts can invoke an already-running Harrier MCP endpoint, but they do not host or deploy Harrier.

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
| 2. Demo EMR baseline infra | Not started | harrier-emr-demo-lab | Add VPC, S3, EMR, IAM, logging, lifecycle, cost controls. |
| 3. Happy path Spark job | Not started | harrier-emr-demo-lab | Generate data, submit EMR step, export investigation context. |
| 10. Demo scenarios batch 1 | Not started | harrier-emr-demo-lab | `executor_oom`, `driver_oom`, `missing_dependency`, `s3_access_denied`, `bad_input_data`. |
| 14. Demo scenarios batch 2 | Not started | harrier-emr-demo-lab | Advanced Spark/IAM/DB/Livy/storage scenarios. |
| 19. Scenario validation harness | Started | harrier-emr-demo-lab | Placeholder script exists. |

## Next Session Start Here

Recommended next task:

1. Implement baseline Terraform for demo EMR on EC2.
2. Include cost and retention controls from the start:
   - EMR auto-termination
   - S3 lifecycle rules
   - CloudWatch log retention
   - `Project=harrier-demo` and `Environment=demo` tags
3. Keep resource names prefixed with `harrier-demo`.
4. Do not add MCP server code to this repo.

## Open Questions

- Confirm target AWS region for demo default: currently `ap-southeast-2`.
- Confirm allowed instance types and max runtime for demo clusters.
- Decide whether budget alarm is Terraform-managed or documented as an account-level setup step.

## Useful Commands

```bash
cd /Users/pinakimukherjee/Documents/Workspace/harrier-emr-demo-lab
python3 -m compileall scripts spark-jobs db
find . -maxdepth 3 -type f | sort
```


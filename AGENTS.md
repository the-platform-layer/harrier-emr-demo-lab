# Agent Guide

This file is the fastest orientation path for AI coding agents and human maintainers working in Harrier EMR Demo Lab.

## Product Boundary

Harrier EMR Demo Lab creates disposable AWS scenarios that validate Harrier EMR MCP against real EMR failures. It owns Terraform infrastructure, Spark jobs, scenario runners, expected findings, validation scripts, cleanup docs, and cost controls.

The production MCP server lives in the sibling `harrier-emr-mcp` repository.

## Safety Defaults

- This repo can create real AWS resources and real cost. Assume sandbox account usage.
- Prefer bounded, reproducible failure scenarios over open-ended stress tests.
- Keep cleanup paths obvious and tested when adding infrastructure or scenarios.
- Never commit Terraform state, generated data, validation reports, credentials, or `.harrier-demo/` output.
- Document any scenario that intentionally breaks IAM, S3, KMS, Kubernetes scheduling, or data quality.

## Where To Work

| Area | Path |
| --- | --- |
| Terraform infrastructure | `infra/terraform/` |
| Spark jobs | `spark-jobs/` |
| Scenario configs | `scenario-configs/` |
| Expected findings | `expected-findings/` |
| Scenario runners | `scripts/run_scenario.sh`, `scripts/submit_*.sh` |
| Validation harness | `validation/`, `scripts/validate_scenario.sh` |
| MWAA local runner | `mwaa-local/` |
| Tests | `tests/` |
| Docs | `docs/` |
| Examples | `examples/` |

## Local Commands

```bash
make test
make smoke
```

For Terraform edits:

```bash
terraform -chdir=infra/terraform fmt -check -recursive
terraform -chdir=infra/terraform init -backend=false
terraform -chdir=infra/terraform validate
```

For live validation, set the required AWS and Harrier endpoint variables, then run one scenario at a time:

```bash
SCENARIO=s3_access_denied RUNTIME=emr_ec2 make run-scenario
SCENARIO=s3_access_denied RUNTIME=emr_ec2 make validate
```

## Scenario Checklist

- Add or update `scenario-configs/<scenario>.json`.
- Add or update `expected-findings/<scenario>.json`.
- Add Spark job code under `spark-jobs/<scenario>/` when needed.
- Update `docs/scenarios.md`, `docs/expected-findings.md`, and `docs/validation-matrix.md`.
- Add tests for static wiring and runtime-specific support.
- Confirm cleanup handles created resources and temporary data.

## Non-Goals

- Do not implement Harrier MCP diagnosis logic here; use `harrier-emr-mcp`.
- Do not run broad live scenario batches by default in CI.
- Do not make the default Terraform deployment depend on an image that has not been pushed yet.

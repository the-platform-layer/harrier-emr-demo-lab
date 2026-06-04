# Contributing To Harrier EMR Demo Lab

This repo contains the disposable AWS demo environment for Harrier EMR MCP.
Contributions should make scenarios safer, clearer, cheaper, or easier to
validate.

## Before You Start

- Read [AGENTS.md](AGENTS.md) for the repository boundary, safety defaults, and
  source layout.
- Use a sandbox AWS account for live testing. This repository can create real
  resources, intentional Spark failures, and real cost.
- Open an issue before adding new AWS services, changing Terraform topology,
  changing cleanup behavior, or introducing a scenario with unusual cost or
  risk.
- Do not commit generated validation output, Terraform state, `.env` files,
  credentials, account IDs, or raw logs.

## Local Checks

```bash
make test
make hygiene
make smoke
```

Many live validation paths require AWS credentials and are not expected to run
in every pull request.

## Pull Request Checklist

- Keep generated files out of git.
- Document any new AWS service or permission.
- Add expected findings for new scenarios.
- Add cleanup behavior for resources created by new scenarios.
- Update the scenario catalog when adding or changing scenarios.
- Prefer simulations over destructive mutations.

## Live Validation Expectations

Run live checks one scenario at a time and record what you validated:

```bash
SCENARIO=s3_access_denied RUNTIME=emr_ec2 make run-scenario
SCENARIO=s3_access_denied RUNTIME=emr_ec2 make validate
make destroy
```

For Terraform changes, also run:

```bash
terraform -chdir=infra/terraform fmt -check -recursive
terraform -chdir=infra/terraform init -backend=false
terraform -chdir=infra/terraform validate
```

## Adding A Scenario

1. Add a scenario config under `scenario-configs/`.
2. Add a Spark job or submitter behavior.
3. Add expected findings.
4. Add docs for runtime support, cost/risk, and cleanup.
5. Add static tests for config shape and validation harness behavior.

## Repository Boundary

This repository owns demo infrastructure, scenario execution, expected findings,
and validation harnesses. The production MCP server, report renderer, runtime
collectors, and DevOps Agent integration live in the `harrier-emr-mcp`
repository.

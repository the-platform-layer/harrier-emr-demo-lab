# Support

Harrier EMR Demo Lab helps validate Harrier EMR MCP with disposable AWS scenarios.

## Where To Ask

| Need | Best Path |
| --- | --- |
| Scenario does not deploy, run, validate, or clean up | Open a bug report with the scenario name and runtime |
| New failure scenario request | Open a scenario request |
| Cost, retention, or cleanup concern | Start with `docs/cost-and-retention.md` and `docs/cleanup.md`, then open an issue |
| Security vulnerability or accidental credential exposure | Follow `SECURITY.md`; do not open a public issue |

## What To Include

For scenario issues, include:

- Runtime: EMR on EC2, EMR Serverless, EMR on EKS, or MWAA local runner.
- Scenario name.
- Command that failed.
- Redacted AWS region/account context.
- Redacted output from the scenario runner or validation report.
- Whether cleanup was completed.

## Scope

This project can help with reproducible demo infrastructure and validation behavior. It cannot provide production incident response or review private AWS accounts through public GitHub issues.

## Cost Reminder

This repo can create real AWS resources. Use a sandbox account, set budgets where possible, and run `make destroy` when validation is complete.

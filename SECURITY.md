# Security Policy

## Supported Versions

Only the latest demo-lab code on `main` is supported.

| Version | Supported |
| --- | --- |
| latest | Yes |
| older | No |

## Reporting A Vulnerability

Do not open a public issue for credentials, account exposure, vulnerable IAM,
or unsafe Terraform behavior. Use GitHub private vulnerability reporting when
available, or contact the maintainers privately.

## Demo Safety Scope

This repository creates real AWS resources and intentionally triggers controlled
failure scenarios. Run it only in a sandbox or demo account.

Sensitive areas include:

- Terraform IAM roles and policies
- S3 buckets used for raw data, processed data, and logs
- EMR, EMR Serverless, EMR on EKS, EKS, RDS, and MWAA-local resources
- generated validation output under `.harrier-demo/`
- local `.env` files and Terraform variable files

## Safety Rules

- Never commit `.harrier-demo/`, generated data, Terraform state, or credentials.
- Use a budget alarm before running live scenarios.
- Destroy resources when validation is complete.
- Redact account IDs and logs before opening public issues.

See [docs/cost-and-retention.md](docs/cost-and-retention.md) and
[docs/cleanup.md](docs/cleanup.md).


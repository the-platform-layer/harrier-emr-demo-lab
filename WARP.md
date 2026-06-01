# Warp Guide

Harrier EMR Demo Lab validates Harrier MCP with disposable AWS EMR failure scenarios.

## Common Commands

```bash
make test
make smoke
make deploy
SCENARIO=s3_access_denied RUNTIME=emr_ec2 make run-scenario
SCENARIO=s3_access_denied RUNTIME=emr_ec2 make validate
make destroy
```

## Terraform Checks

```bash
terraform -chdir=infra/terraform fmt -check -recursive
terraform -chdir=infra/terraform init -backend=false
terraform -chdir=infra/terraform validate
```

## Safety Notes

Use a sandbox AWS account. Destroy lab resources after validation, and do not commit generated `.harrier-demo/` output, Terraform state, or credentials.

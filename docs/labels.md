# GitHub Labels

Harrier EMR Demo Lab stores its public label taxonomy in
[`.github/labels.json`](../.github/labels.json). The `Sync Labels` workflow
creates or updates those labels in GitHub.

The workflow is intentionally non-destructive: it does not delete labels that
are not in the JSON file.

## Label Taxonomy

| Label | Purpose |
| --- | --- |
| `bug` | Incorrect scenario, script, or validation behavior |
| `enhancement` | New demo-lab capability |
| `docs` | Documentation-only change |
| `security` | IAM, credential, or vulnerable configuration work |
| `cost-control` | Budget, retention, cleanup, or destroy behavior |
| `scenario` | Scenario config or Spark job work |
| `runtime/ec2` | EMR on EC2 scenario support |
| `runtime/serverless` | EMR Serverless scenario support |
| `runtime/eks` | EMR on EKS scenario support |
| `validation` | Harness and expected findings |
| `needs-triage` | Needs maintainer review before prioritization |
| `dependencies` | Automated dependency update |
| `github-actions` | GitHub Actions dependency or workflow update |
| `docker` | Dockerfile or container dependency update |
| `terraform` | Terraform provider, module, or infrastructure dependency update |
| `good first issue` | Scoped contributor-friendly task |
| `help wanted` | Maintainer-approved external contribution |

## Sync Labels

Run the workflow manually after changing labels:

```bash
gh workflow run "Sync Labels" --repo the-platform-layer/harrier-emr-demo-lab
```

The workflow also runs on pushes that change `.github/labels.json`.

# Public Release Checklist

Use this checklist before making the repository public or cutting a documented
demo-lab release.

## Repository Surface

- Confirm repository description, website, and topics describe a disposable AWS
  demo lab.
- Confirm Issues are enabled.
- Confirm the GitHub social preview uses `docs/assets/social-preview.png`.
- Run the `Sync Labels` workflow after any label taxonomy change.
- Confirm `README.md`, `SECURITY.md`, `SUPPORT.md`, `CONTRIBUTING.md`,
  `CODE_OF_CONDUCT.md`, `MAINTAINERS.md`, `ROADMAP.md`, `CHANGELOG.md`, and
  `LICENSE` are present.

## Local Validation

```bash
make hygiene
make test
make smoke
```

For Terraform changes:

```bash
terraform -chdir=infra/terraform fmt -check -recursive
terraform -chdir=infra/terraform init -backend=false
terraform -chdir=infra/terraform validate
```

## Demo Safety

- Confirm default CI does not run live AWS scenarios.
- Confirm live scenario workflows remain manual.
- Confirm `.harrier-demo/`, `.harrier-local/`, `comparison-output/`, generated
  sample data, Terraform state, and credentials remain ignored.
- Confirm docs link to [cost-and-retention.md](cost-and-retention.md) and
  [cleanup.md](cleanup.md).
- Confirm every new scenario documents runtime coverage, expected finding,
  cleanup behavior, and cost or risk notes.

## Public Documentation

- Confirm README links work in a clean checkout.
- Confirm scenario docs do not refer to obsolete slice names or internal
  planning language.
- Confirm demo docs point to the public Harrier docs for MCP server setup and
  DevOps Agent integration.
- Confirm social preview and README hero images render correctly.

## Release

- Update `CHANGELOG.md`.
- Confirm CI is green on `main`.
- Confirm release notes call out new scenarios, Terraform resources, AWS
  permissions, cleanup changes, or validation harness changes.
- Push a semver tag only for documented public milestones:

  ```bash
  git tag v0.1.0
  git push origin v0.1.0
  ```

- Confirm the GitHub release appears in the repository right pane.

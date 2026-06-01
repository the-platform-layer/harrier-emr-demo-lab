# CI And Release

The demo lab is intentionally conservative in CI. Pull requests run static and
unit-level checks only. Live AWS scenario execution remains manual because it
creates resources and cost.

## Pull Request Gates

- Python harness tests
- Terraform format check
- Terraform validate
- Markdown lint
- Link check
- Secret scan
- CodeQL

## Manual Scenario Smoke

The `scenario-smoke-test` workflow is manual. It records the requested scenario
and runtime, runs static tests, and documents the live prerequisites. Extend it
with environment-protected AWS credentials only in a sandbox account.

## Release Policy

The demo lab does not publish runtime artifacts. Use GitHub releases only for
documented milestones or companion releases aligned to Harrier EMR MCP.


# Maintainers

This project is maintained by the Harrier EMR Demo Lab maintainers.

## Maintainer Responsibilities

- Keep scenarios reproducible and bounded.
- Keep cleanup paths documented and working.
- Review Terraform changes for cost, security, and teardown behavior.
- Keep expected findings aligned with Harrier EMR MCP.
- Avoid live AWS execution in default CI.

## Review Areas

| Area | Review Expectations |
| --- | --- |
| Terraform | Check cost impact, least privilege, cleanup, and validation |
| Scenario runners | Check runtime flags, generated context, logs, and failure determinism |
| Spark jobs | Check that failures are intentional, bounded, and observable |
| Expected findings | Check finding IDs, evidence expectations, and validation output |
| Docs | Check copy-paste commands, warnings, and cleanup steps |

## Decision Process

Small fixes can be merged after normal review and passing CI. Changes that alter AWS topology, default cost posture, scenario lifecycle, or validation semantics should add an Architecture Decision Record under `docs/adr/`.

## Release Stewardship

Changes should update `CHANGELOG.md` when they add scenarios, change Terraform resources, alter validation behavior, or modify cleanup expectations.

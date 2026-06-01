# Copilot Instructions

Harrier EMR Demo Lab owns disposable AWS scenarios for validating Harrier EMR MCP.

Follow the repository guidance in `AGENTS.md`.

Prefer existing project patterns:

- Scenario definitions belong in `scenario-configs/`.
- Expected classifier results belong in `expected-findings/`.
- Spark jobs belong in `spark-jobs/<scenario>/`.
- Runtime submission logic belongs in `scripts/submit_step.sh`, `scripts/submit_serverless_job.sh`, or `scripts/submit_eks_job.sh`.
- Validation behavior belongs in `validation/` and `scripts/validate_scenario.sh`.
- Documentation changes should update the scenario catalog and validation matrix.

Do not make CI run live AWS scenarios by default. Keep live scenario execution behind manual commands or workflow dispatch.

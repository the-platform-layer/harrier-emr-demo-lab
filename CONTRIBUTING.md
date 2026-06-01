# Contributing To Harrier EMR Demo Lab

This repo contains the disposable AWS demo environment for Harrier EMR MCP.
Contributions should make scenarios safer, clearer, cheaper, or easier to
validate.

## Local Checks

```bash
python3 -m pytest -q
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

## Adding A Scenario

1. Add a scenario config under `scenario-configs/`.
2. Add a Spark job or submitter behavior.
3. Add expected findings.
4. Add docs for runtime support, cost/risk, and cleanup.
5. Add static tests for config shape and validation harness behavior.


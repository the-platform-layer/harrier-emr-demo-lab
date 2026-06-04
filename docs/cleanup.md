# Cleanup

Use `scripts/cleanup_scenario.sh` after individual scenario runs and `scripts/destroy.sh` to remove demo infrastructure.

The destroy flow should print resources before deletion.

Scenario cleanup uses the latest context for the requested scenario:

```bash
./scripts/cleanup_scenario.sh executor_oom
```

It removes the scenario output prefix, generated input object when present, uploaded job object, and locally generated sample data. It also tries to cancel the EMR step if it is still active. Set `CLEAN_CONTEXT=true` to remove the selected run context after cleanup.

For baseline infrastructure:

```bash
./scripts/destroy.sh
```

You must type:

```text
destroy-harrier-demo
```

before Terraform destroy runs.

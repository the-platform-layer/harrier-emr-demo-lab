# Cleanup

Use `scripts/cleanup_scenario.sh` after individual scenario runs and `scripts/destroy.sh` to remove demo infrastructure.

The destroy flow should print resources before deletion.

For Slice 2 baseline infrastructure:

```bash
./scripts/destroy.sh
```

You must type:

```text
destroy-harrier-demo
```

before Terraform destroy runs.

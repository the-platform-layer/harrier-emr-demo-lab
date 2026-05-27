# DevOps Agent Demo Flow

1. Deploy the demo lab.
2. Run a demo scenario.
3. Export investigation context.
4. Ask AWS DevOps Agent to investigate the EMR incident with Harrier.
5. Harrier receives normal MCP investigation inputs; it does not receive demo scenario commands.

The exported investigation context should include `deploy_mode` when known so Harrier can choose the correct driver log layout.

For a baseline check before failure demos, run:

```bash
./scripts/run_scenario.sh happy_path
./scripts/export_investigation_context.sh
```

For the long-running demo, export context while the EMR step is still running:

```bash
./scripts/run_scenario.sh long_running_data_delay
./scripts/export_investigation_context.sh
```

The exported JSON includes `job_state=running` and normalized `diagnostic_signals` for the early classifier path.

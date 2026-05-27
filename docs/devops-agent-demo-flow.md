# DevOps Agent Demo Flow

1. Deploy the demo lab.
2. Run a demo scenario.
3. Export investigation context.
4. Ask AWS DevOps Agent to investigate the EMR incident with Harrier.
5. Harrier receives normal MCP investigation inputs; it does not receive demo scenario commands.

The exported investigation context should include `deploy_mode` when known so Harrier can choose the correct driver log layout.

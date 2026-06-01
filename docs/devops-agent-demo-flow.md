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

## Runtime Parity Prompt Set

Use these prompts after the Harrier MCP server is registered in AWS DevOps Agent. They use live validation IDs from the demo lab and should be run from a read-only Agent Space.

EMR Serverless happy path:

```text
Use Harrier to investigate EMR Serverless application 00g63elinhft1g29 in ap-southeast-2. The job run id is 00g642d6r2tpn82b. Return the root cause, supporting evidence, and warnings. This was a successful job, so verify there is no false positive.
```

Expected category: `UNKNOWN`

EMR Serverless failure:

```text
Use Harrier to investigate EMR Serverless application 00g63elinhft1g29 in ap-southeast-2. The job run id is 00g642g68ooqh82b. Return the root cause, driver or executor evidence, warnings, and dry-run PR-ready recommendations.
```

Expected category: `DEPENDENCY_MISSING`

EMR on EKS with Kubernetes access:

```text
Use Harrier to investigate EMR on EKS virtual cluster rhqipmqf1s7e37r25ftwltvt0 in ap-southeast-2. The job run id is 000000037k0don5oufg, EKS cluster name is harrier-demo-eks, and namespace is harrier-emr-jobs. Include Kubernetes pod evidence if available.
```

Expected category: `EKS_IMAGE_PULL_FAILURE` when the image-pull pod evidence is still available.

EMR on EKS without Kubernetes access:

```text
Use Harrier to investigate EMR on EKS virtual cluster rhqipmqf1s7e37r25ftwltvt0 in ap-southeast-2. The job run id is 000000037jsp9f10kl1, EKS cluster name is harrier-demo-eks, and namespace is harrier-emr-jobs. Return EMR Containers metadata, log evidence, and any Kubernetes access warnings.
```

Expected category: `S3_ACCESS_DENIED`. If the Agent Space or MCP runtime cannot read Kubernetes pods, Harrier should still complete the investigation and include a recoverable Kubernetes diagnostics warning.

Registration itself is completed in the AWS DevOps Agent console or control plane. The demo lab cannot perform that registration directly; it supplies runtime IDs, validation evidence, and prompts for the registered MCP server.

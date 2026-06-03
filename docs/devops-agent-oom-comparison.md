# DevOps Agent OOM Comparison

This runbook compares how deeply AWS DevOps Agent investigates the same Spark
executor OOM failure with and without Harrier MCP.

The comparison uses the existing `executor_oom` scenario across:

- EMR on EC2
- EMR Serverless
- EMR on EKS

## Goal

Run the same failure shape through two investigation lanes:

| Lane | Agent Space Setup | Purpose |
| --- | --- | --- |
| Native DevOps Agent | No Harrier tools allowlisted | Establish the AWS-native baseline. |
| DevOps Agent with Harrier MCP | Harrier read-only tools allowlisted | Measure the extra EMR/Spark diagnosis depth Harrier adds. |

Do not run both lanes in the same Agent Space unless you can guarantee the native
prompt cannot call Harrier tools.

## Prerequisites

Before running the comparison:

1. Deploy the demo lab infrastructure.
2. Ensure EC2, Serverless, and EKS runtimes are available.
3. Register Harrier MCP with AWS DevOps Agent.
4. Create or choose two read-only Agent Spaces:
   - native baseline: no Harrier custom MCP server enabled
   - Harrier lane: Harrier MCP enabled with read-only tools
5. Confirm the Harrier lane allowlists only:
   - `harrier_start_emr_investigation`
   - `harrier_get_investigation_report`
   - `harrier_get_evidence`
   - `harrier_prepare_pr` with dry-run behavior only

## Submit Fresh OOM Runs

From the demo lab repo:

```bash
AWS_ACCOUNT_ID=123456789012 \
./scripts/run_devops_agent_oom_comparison.sh
```

The script submits `executor_oom` to each runtime, waits for terminal state where
possible, exports runtime-aware investigation context, and writes comparison
artifacts under:

```text
.harrier-demo/comparisons/oom-<timestamp>/
```

Important generated files:

| File | Use |
| --- | --- |
| `prompts.md` | Copy/paste prompt set for both Agent Spaces. |
| `scorecard.md` | Manual scoring rubric for native vs Harrier outputs. |
| `metadata.json` | Comparison metadata. |
| `contexts/*-exported.json` | Runtime-aware investigation context. |
| `responses/*.md` | Suggested location to save Agent responses. |

## Use Existing Runs

If the OOM jobs already ran, pass existing context files:

```bash
SKIP_SCENARIO_RUN=1 \
AWS_ACCOUNT_ID=123456789012 \
./scripts/run_devops_agent_oom_comparison.sh \
  --context emr_ec2=.harrier-demo/runs/executor_oom-ec2.json \
  --context emr_serverless=.harrier-demo/runs/executor_oom-serverless.json \
  --context emr_eks=.harrier-demo/runs/executor_oom-eks.json
```

Environment variable alternatives:

```bash
export EMR_EC2_CONTEXT_FILE=.harrier-demo/runs/executor_oom-ec2.json
export EMR_SERVERLESS_CONTEXT_FILE=.harrier-demo/runs/executor_oom-serverless.json
export EMR_EKS_CONTEXT_FILE=.harrier-demo/runs/executor_oom-eks.json
```

Then run:

```bash
SKIP_SCENARIO_RUN=1 \
AWS_ACCOUNT_ID=123456789012 \
./scripts/run_devops_agent_oom_comparison.sh
```

## Run The Agent Comparison

1. Open `prompts.md`.
2. Copy each Native DevOps Agent prompt into the native-baseline Agent Space.
3. Save each response under:

   ```text
   responses/native-emr_ec2.md
   responses/native-emr_serverless.md
   responses/native-emr_eks.md
   ```

4. Copy each Harrier prompt into the Harrier-enabled Agent Space.
5. Save each response under:

   ```text
   responses/harrier-emr_ec2.md
   responses/harrier-emr_serverless.md
   responses/harrier-emr_eks.md
   ```

6. Fill in `scorecard.md`.

## What To Compare

The scorecard intentionally measures depth, not just correctness:

- Did it identify executor OOM rather than generic Spark failure?
- Did it distinguish executor failure from driver failure?
- Did it cite runtime-specific evidence?
- Did it include bounded log excerpts?
- Did it say what was not checked?
- Did recommendations differ for EC2/YARN, Serverless worker sizing, and EKS pod resources?
- Did it avoid unsafe mutations?
- Was the answer usable for an on-call operator?

## Expected High-Level Result

Both lanes may identify memory pressure if CloudWatch and logs are available.
Harrier should be stronger at:

- consistent visual check maps
- separating observed facts from interpretation
- explicit `NOT_CHECKED` and `INCONCLUSIVE` checks
- runtime-specific Spark recommendations
- producing a repeatable Initial Diagnosis Report

Native DevOps Agent may be stronger at broader topology or deployment
correlation, depending on Agent Space integrations.

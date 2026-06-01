# Demo Lab DevOps Agent Prompts

## Fresh EC2 Infra Failure

```text
I ran the Harrier demo-lab s3_access_denied scenario. Use Harrier to investigate
the exported EMR cluster and step context. Show the initial diagnosis report,
visual check map, evidence cards, log excerpts, inconclusive checks, and next
steps. Treat this as initial triage, not final RCA.
```

## Fresh Serverless Data Failure

```text
I ran the Harrier demo-lab bad_input_data scenario on EMR Serverless. Use Harrier
to investigate the application and job run. Explain whether this looks like
infrastructure, data, Spark runtime, observability, or configuration.
```

## Fresh EKS Pod Failure

```text
I ran the Harrier demo-lab image_pull_failure scenario on EMR on EKS. Use Harrier
to inspect the EMR Containers job run and Kubernetes pod evidence if available.
Show whether the failure is Spark-level or Kubernetes-level.
```

## Validation Report Review

```text
Review the latest Harrier demo-lab validation JSON for this scenario. Summarize
whether the expected finding matched the actual finding, and explain any mismatch
without dumping raw JSON.
```


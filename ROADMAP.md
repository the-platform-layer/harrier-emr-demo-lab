# Roadmap

This roadmap is intentionally high level. It describes the direction for Harrier EMR Demo Lab without promising specific delivery dates.

## Current Focus

- Keep live validation scenarios reproducible, bounded, and easy to clean up.
- Cover representative EMR on EC2, EMR Serverless, and EMR on EKS failures.
- Keep expected findings aligned with Harrier EMR MCP diagnosis behavior.
- Make DevOps Agent demo flows easy to run and explain.

## Near-Term Work

| Area | Direction |
| --- | --- |
| Serverless scenarios | Broader coverage for monitoring config, worker sizing, missing inputs, and dependency failures |
| EKS scenarios | Stronger pod pending, image pull, executor OOM, and S3 access scenarios |
| Validation harness | Better summaries, clearer failure diffs, and runtime-specific context exports |
| Cost controls | More explicit teardown checks and safer defaults for optional services |
| Documentation | More copy-paste prompts and scenario walkthroughs for demos |

## Later Work

- Scheduled demo environment drift checks.
- Additional database and metastore failure patterns.
- Optional benchmark-style scenario batches for regression comparison.
- More sample reports that pair scenario output with Harrier diagnosis.

## Out Of Scope For Now

- Running live AWS scenarios automatically on every pull request.
- Keeping long-lived production-like EMR clusters alive by default.
- Implementing Harrier MCP diagnosis logic in this repo.

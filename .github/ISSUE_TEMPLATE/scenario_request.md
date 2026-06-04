---
name: Scenario request
about: Request a new controlled EMR failure scenario
title: "[Scenario]: "
labels: scenario, needs-triage
assignees: ""
---

## Failure To Demonstrate

What should Harrier diagnose?

## Expected Finding

Example: `S3_ACCESS_DENIED`, `BAD_INPUT_DATA`, `EXECUTOR_OOM`.

## Runtime

- [ ] EMR on EC2
- [ ] EMR Serverless
- [ ] EMR on EKS

## Safe Simulation Idea

How can this be triggered without mutating production-like resources?

## Evidence Harrier Should Collect

- [ ] EMR API metadata
- [ ] S3 step or container logs
- [ ] CloudWatch logs
- [ ] CloudWatch metrics
- [ ] Kubernetes pod diagnostics
- [ ] Other:

## Cost And Cleanup Notes

- What resources are required?
- What should cleanup delete?
- Is a budget or runtime limit needed?

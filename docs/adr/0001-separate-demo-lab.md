# ADR 0001: Keep Live Scenarios In A Separate Demo Lab

## Status

Accepted.

## Context

Harrier EMR MCP needs real-world validation against EMR on EC2, EMR Serverless, and EMR on EKS failures. Those scenarios require disposable AWS infrastructure, generated data, Spark jobs, IAM policies, Kubernetes resources, and cleanup workflows.

Mixing those live resources into the MCP server repository would blur production code with demo infrastructure and make the core server harder to review.

## Decision

Live AWS scenarios remain in Harrier EMR Demo Lab. The MCP repository owns diagnosis behavior, tool contracts, collectors, and recommendations. The demo lab owns infrastructure, scenario orchestration, expected findings, and validation harnesses.

## Consequences

- The MCP repo stays smaller and easier to reason about.
- Demo infrastructure can include stronger cost warnings and cleanup workflows.
- Scenario changes must keep expected findings aligned with MCP behavior.
- Cross-repo documentation must stay clear about which repository owns each concern.

# Architecture Decision Records

Architecture Decision Records capture choices that shape the demo lab's AWS topology, safety posture, scenario design, and validation behavior.

## When To Add An ADR

Add an ADR when a change:

- Alters default AWS infrastructure or cost posture.
- Adds a new supported runtime class.
- Changes how scenario context is exported to Harrier.
- Changes validation report semantics.
- Adds long-running or stateful resources.

## Format

Use this structure:

```markdown
# ADR N: Title

## Status

Accepted, proposed, superseded, or deprecated.

## Context

What problem or constraint led to the decision?

## Decision

What did we choose?

## Consequences

What improves, what gets harder, and what must be watched?
```

## Records

- [ADR 0001: Keep Live Scenarios In A Separate Demo Lab](0001-separate-demo-lab.md)

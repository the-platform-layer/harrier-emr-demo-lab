# Local Developer Experience

The demo lab uses Make targets as a contributor-friendly wrapper around the
existing scripts.

## Setup

```bash
cp .env.example .env
```

## Common Commands

```bash
make test
make deploy
SCENARIO=s3_access_denied RUNTIME=emr_ec2 make run-scenario
SCENARIO=s3_access_denied RUNTIME=emr_ec2 make validate
make destroy
```

## Generated Output

The harness writes generated context and validation output under `.harrier-demo/`.
That directory is intentionally ignored and should not be committed.

## Safety

Live commands can create AWS cost. Run them in a sandbox account and destroy the
lab when validation is complete.


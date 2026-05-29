# Harrier MWAA Local Runner

This folder contains the Harrier demo overlay for AWS's MWAA-compatible local runner image.

The build uses `aws/aws-mwaa-local-runner` as the base image source, then layers in:

- Harrier demo DAGs
- Existing scenario runner scripts
- Existing Spark jobs
- Existing scenario configs

The ECS deployment runs the container in low-cost demo mode with `SequentialExecutor` inside one Fargate task. It is meant to mimic the DAG/operator experience for demos, not replace production Amazon MWAA.

## Build And Push

```bash
scripts/build_mwaa_local_runner_image.sh --repository-url <ecr-repository-url> --push
```

## Deploy To ECS

```bash
scripts/deploy_mwaa_local_runner.sh
```

The deploy helper creates the ECR repository first, builds and pushes the image, then applies the ECS service.

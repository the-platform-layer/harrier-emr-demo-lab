# EMR On EKS Prerequisites

Slice 31 assumes an existing EKS cluster. The demo lab registers one namespace as an EMR on EKS virtual cluster and submits disposable Spark jobs into that namespace.

## Required Inputs

- `EMR_EKS_CLUSTER_NAME` or Terraform variable `emr_eks_cluster_name`
- `EMR_EKS_NAMESPACE`, default `harrier-emr-jobs`
- `EMR_EKS_JOB_ROLE_ARN` or Terraform variable `emr_eks_job_role_arn`
- AWS CLI access to `eks`, `emr-containers`, `s3`, and `logs`
- `kubectl` access to create/read pods in the target namespace
- `eksctl` is recommended for the EMR on EKS access entry setup

## Setup Flow

Prepare namespace access and update the job role trust policy:

```bash
EMR_EKS_CLUSTER_NAME=analytics-dev \
EMR_EKS_JOB_ROLE_ARN=arn:aws:iam::123456789012:role/harrier-demo-emr-eks-job \
./scripts/setup_eks_virtual_cluster.sh
```

Register the namespace as an EMR virtual cluster:

```bash
terraform -chdir=infra/terraform apply \
  -var enable_emr_eks=true \
  -var emr_eks_cluster_name=analytics-dev \
  -var emr_eks_namespace=harrier-emr-jobs \
  -var emr_eks_job_role_arn=arn:aws:iam::123456789012:role/harrier-demo-emr-eks-job
```

The Terraform output `emr_eks_virtual_cluster_id` is used by `scripts/submit_eks_job.sh`.

## Kubernetes Access For Harrier

Harrier can investigate EMR on EKS without Kubernetes API access, but pod diagnostics are much more useful when it can read pods in the target namespace.

Grant read-only access for:

- pods
- pod status
- events

No write access is required for Harrier investigation. The demo submitter can create job-run pods only through EMR Containers.

## Live Validation

Run one scenario through Harrier:

```bash
AWS_ACCOUNT_ID=123456789012 \
RUNTIME=emr_eks \
./scripts/validate_scenario.sh image_pull_failure
```

The validation harness sends:

```json
{
  "runtime": "emr_eks",
  "target": {
    "virtual_cluster_id": "vc-1234567890abcdef0",
    "job_run_id": "job-run-123",
    "eks_cluster_name": "analytics-dev",
    "namespace": "harrier-emr-jobs"
  }
}
```

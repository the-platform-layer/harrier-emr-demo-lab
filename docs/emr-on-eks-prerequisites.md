# EMR On EKS Prerequisites

The EMR on EKS demo can use an existing EKS cluster or create a disposable demo
cluster. The demo lab registers one namespace as an EMR on EKS virtual cluster
and submits disposable Spark jobs into that namespace.

## Disposable Demo Cluster

Create the demo EKS cluster, managed node group, and EMR on EKS job role:

```bash
terraform -chdir=infra/terraform apply \
  -var enable_demo_eks_cluster=true
```

Prepare namespace access and update the job role trust policy:

```bash
./scripts/setup_eks_virtual_cluster.sh
```

Register the namespace as an EMR virtual cluster:

```bash
terraform -chdir=infra/terraform apply \
  -var enable_demo_eks_cluster=true \
  -var enable_emr_eks=true
```

The disposable cluster creates billable EKS and EC2 resources. Destroy it after validation:

```bash
terraform -chdir=infra/terraform destroy \
  -var enable_demo_eks_cluster=true \
  -var enable_emr_eks=true
```

## Required Inputs

For an existing cluster:

- `EMR_EKS_CLUSTER_NAME` or Terraform variable `emr_eks_cluster_name`
- `EMR_EKS_NAMESPACE`, default `harrier-emr-jobs`
- `EMR_EKS_JOB_ROLE_ARN` or Terraform variable `emr_eks_job_role_arn`

For the disposable demo cluster, Terraform outputs the cluster name and job role ARN.

- AWS CLI access to `eks`, `emr-containers`, `s3`, and `logs`
- `kubectl` access to create/read pods in the target namespace
- `eksctl` is optional; the setup script falls back to `kubectl` RBAC plus EKS Access Entry integration when it is not installed

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

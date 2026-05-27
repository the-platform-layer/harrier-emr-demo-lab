# Cost And Retention

Required controls:

- EMR auto-termination policy
- Smallest practical instance sizes
- RDS disabled by default until DB scenarios are enabled
- S3 lifecycle expiration
- CloudWatch log retention
- Optional AWS Budget or cost alarm

Default retention targets:

- Raw sample data: 7 days
- Processed sample output: 7 days
- EMR/Spark logs: 14 days
- Validation reports: 30 days
- Demo secrets: delete on destroy

## Slice 2 Defaults

Terraform creates:

- One demo VPC.
- One public subnet for EMR on EC2.
- Three S3 buckets:
  - raw demo input
  - processed demo output
  - archived EMR/Spark logs
- One EMR cluster with Spark and Livy.
- One EMR service role.
- One EMR EC2 instance profile.
- CloudWatch alarms with actions disabled.
- One demo CloudWatch log group with finite retention.

Default retention:

- Raw S3 data expires after `raw_data_retention_days`, default 7.
- Processed S3 data expires after `processed_data_retention_days`, default 7.
- EMR/Spark logs expire after `emr_log_retention_days`, default 14.
- CloudWatch logs expire after `cloudwatch_log_retention_days`, default 14.

Default cost controls:

- Resource names are prefixed with `harrier-demo`.
- Resources use default tags `Project=harrier-demo` and `Environment=demo`.
- RDS resources are disabled in Slice 2.
- S3 buckets use lifecycle expiration and `force_destroy_buckets=true` by default.
- EMR auto-termination is configured with `max_runtime_hours`, default 4 idle hours.

Important: EMR auto-termination is an idle timeout, not a guaranteed wall-clock cutoff if the cluster remains busy.

## Budget Setup

Terraform outputs a `budget_setup_note`. For demo account safety, create either:

- an AWS Budget filtered to the `Project=harrier-demo` cost allocation tag, or
- an account-level billing alarm around `monthly_budget_limit_usd`, default 100 USD.

Cost allocation tags may need to be activated in the AWS Billing console before tag-filtered budgets work.

## Cleanup

Run:

```bash
./scripts/destroy.sh
```

The destroy script prints Terraform-managed resources and requires the confirmation phrase `destroy-harrier-demo`.

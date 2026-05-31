# Expected Findings

Expected finding JSON files live in `expected-findings/`.

The scenario validation harness compares Harrier's actual root cause category to the expected category for each scenario.

The `happy_path` expected finding is intentionally empty. It is a baseline proof that Harrier can receive context, inspect reachable EMR evidence, and avoid inventing a root cause when the Spark job succeeds.

Slice 10 expected findings cover:

- `executor_oom`
- `driver_oom`
- `missing_dependency`
- `s3_access_denied`
- `bad_input_data`

Each file includes the expected outcome, primary root-cause category, evidence strings Harrier should find, and recommendation type.

Slice 14 expected findings cover advanced Spark, IAM/KMS, storage, DB, and Livy scenarios:

- `data_skew`
- `shuffle_spill`
- `kms_access_denied`
- `hdfs_full`
- `db_connection_failure`
- `db_lock_timeout`
- `db_partition_hotspot`
- `db_large_join_spill`
- `db_bad_sql_plan`
- `livy_session_failure`
- `long_running_data_delay`
- `long_running_resource_delay`
- `long_running_db_delay`

Long-running scenarios should be validated before the Spark step fails. They should assert that Harrier returns a delay explanation, current running state, and whether the likely cause is data, resource, or DB-side work.

DB performance scenarios should also assert `recommendation_type=DB` and `pr_ready=true` when Harrier can produce a reviewed SQL or Spark-code remediation.

The `db_bad_sql_plan` scenario should assert that Harrier uses SQL plan evidence, not only Spark runtime symptoms, before returning `DB_BAD_SQL_PLAN`.

Slice 30 EMR Serverless expected findings reuse the same scenario files for:

- `happy_path`
- `executor_oom`
- `missing_dependency`
- `s3_path_missing`
- `bad_input_data`

The expected root-cause categories do not change by runtime. Serverless validation should additionally prove that the request uses `runtime=emr_serverless` with `target.serverless_application_id` and `target.job_run_id`, and that Harrier reads Serverless S3 or CloudWatch logs instead of EC2 step/YARN paths.

Slice 31 EMR on EKS expected findings reuse existing scenario files for:

- `happy_path`
- `executor_oom`
- `s3_access_denied`

Slice 31 adds EKS-specific expected finding files for:

- `image_pull_failure`
- `pod_pending_resource_pressure`

EKS validation should prove that the request uses `runtime=emr_eks` with `target.virtual_cluster_id`, `target.job_run_id`, `target.eks_cluster_name`, and `target.namespace`. When Kubernetes access is available, Harrier should use pod status evidence to distinguish image pull and scheduling failures from Spark application failures.

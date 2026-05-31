data "aws_iam_policy_document" "emr_serverless_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["emr-serverless.amazonaws.com"]
    }
  }
}

resource "aws_cloudwatch_log_group" "emr_serverless" {
  name              = "/${local.name_prefix}/emr-serverless"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = {
    Name = "${local.name_prefix}-emr-serverless-log-group"
  }
}

resource "aws_iam_role" "emr_serverless_job" {
  name               = "${local.name_prefix}-emr-serverless-job-role"
  assume_role_policy = data.aws_iam_policy_document.emr_serverless_assume_role.json

  tags = {
    Name = "${local.name_prefix}-emr-serverless-job-role"
  }
}

data "aws_iam_policy_document" "emr_serverless_job" {
  source_policy_documents = [
    data.aws_iam_policy_document.emr_demo_s3_access.json,
  ]

  statement {
    sid = "WriteCloudWatchLogs"
    actions = [
      "logs:CreateLogStream",
      "logs:DescribeLogGroups",
      "logs:DescribeLogStreams",
      "logs:PutLogEvents",
    ]
    resources = [
      aws_cloudwatch_log_group.emr_serverless.arn,
      "${aws_cloudwatch_log_group.emr_serverless.arn}:*",
    ]
  }
}

resource "aws_iam_role_policy" "emr_serverless_job" {
  name   = "${local.name_prefix}-emr-serverless-job-access"
  role   = aws_iam_role.emr_serverless_job.id
  policy = data.aws_iam_policy_document.emr_serverless_job.json
}

resource "aws_emrserverless_application" "demo" {
  name          = "${local.name_prefix}-serverless-spark"
  release_label = var.emr_serverless_release_label
  type          = "spark"

  auto_start_configuration {
    enabled = true
  }

  auto_stop_configuration {
    enabled              = true
    idle_timeout_minutes = var.emr_serverless_idle_timeout_minutes
  }

  maximum_capacity {
    cpu    = var.emr_serverless_max_cpu
    memory = var.emr_serverless_max_memory
    disk   = var.emr_serverless_max_disk
  }

  tags = {
    Name = "${local.name_prefix}-serverless-spark"
  }

  depends_on = [
    aws_iam_role_policy.emr_serverless_job,
    aws_s3_bucket_versioning.logs,
  ]
}

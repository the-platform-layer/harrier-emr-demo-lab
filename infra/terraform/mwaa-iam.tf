data "aws_iam_policy_document" "mwaa_task_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "mwaa_execution" {
  name               = "${local.name_prefix}-mwaa-execution-role"
  assume_role_policy = data.aws_iam_policy_document.mwaa_task_assume_role.json

  tags = {
    Name = "${local.name_prefix}-mwaa-execution-role"
  }
}

resource "aws_iam_role_policy_attachment" "mwaa_execution" {
  role       = aws_iam_role.mwaa_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "mwaa_execution_secrets" {
  name = "${local.name_prefix}-mwaa-execution-secrets"
  role = aws_iam_role.mwaa_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ReadAirflowAdminPassword"
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = aws_secretsmanager_secret.mwaa_admin_password.arn
      }
    ]
  })
}

resource "aws_iam_role" "mwaa_task" {
  name               = "${local.name_prefix}-mwaa-task-role"
  assume_role_policy = data.aws_iam_policy_document.mwaa_task_assume_role.json

  tags = {
    Name = "${local.name_prefix}-mwaa-task-role"
  }
}

data "aws_iam_policy_document" "mwaa_task" {
  statement {
    sid = "SubmitAndInspectDemoSteps"
    actions = [
      "elasticmapreduce:AddJobFlowSteps",
      "elasticmapreduce:CancelSteps",
      "elasticmapreduce:DescribeCluster",
      "elasticmapreduce:DescribeStep",
      "elasticmapreduce:ListSteps",
    ]
    resources = ["*"]
  }

  statement {
    sid = "ListDemoBuckets"
    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.raw.arn,
      aws_s3_bucket.processed.arn,
      aws_s3_bucket.logs.arn,
    ]
  }

  statement {
    sid = "ReadWriteDemoObjects"
    actions = [
      "s3:AbortMultipartUpload",
      "s3:DeleteObject",
      "s3:GetObject",
      "s3:ListMultipartUploadParts",
      "s3:PutObject",
    ]
    resources = [
      "${aws_s3_bucket.raw.arn}/*",
      "${aws_s3_bucket.processed.arn}/*",
      "${aws_s3_bucket.logs.arn}/*",
    ]
  }

  statement {
    sid       = "ReadDemoSecrets"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = ["arn:aws:secretsmanager:${var.region}:*:secret:${local.name_prefix}/*"]
  }
}

resource "aws_iam_role_policy" "mwaa_task" {
  name   = "${local.name_prefix}-mwaa-task-policy"
  role   = aws_iam_role.mwaa_task.id
  policy = data.aws_iam_policy_document.mwaa_task.json
}

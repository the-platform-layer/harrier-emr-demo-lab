data "aws_iam_policy_document" "emr_service_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["elasticmapreduce.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "emr_ec2_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "emr_service" {
  name               = "${local.name_prefix}-emr-service-role"
  assume_role_policy = data.aws_iam_policy_document.emr_service_assume_role.json

  tags = {
    Name = "${local.name_prefix}-emr-service-role"
  }
}

resource "aws_iam_role_policy_attachment" "emr_service_managed" {
  role       = aws_iam_role.emr_service.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceRole"
}

resource "aws_iam_role" "emr_ec2" {
  name               = "${local.name_prefix}-emr-ec2-role"
  assume_role_policy = data.aws_iam_policy_document.emr_ec2_assume_role.json

  tags = {
    Name = "${local.name_prefix}-emr-ec2-role"
  }
}

resource "aws_iam_role_policy_attachment" "emr_ec2_managed" {
  role       = aws_iam_role.emr_ec2.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceforEC2Role"
}

data "aws_iam_policy_document" "emr_demo_s3_access" {
  statement {
    sid = "ListDemoBuckets"
    actions = [
      "s3:ListBucket",
      "s3:GetBucketLocation",
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
}

resource "aws_iam_role_policy" "emr_ec2_s3_access" {
  name   = "${local.name_prefix}-emr-demo-s3-access"
  role   = aws_iam_role.emr_ec2.id
  policy = data.aws_iam_policy_document.emr_demo_s3_access.json
}

resource "aws_iam_instance_profile" "emr_ec2" {
  name = "${local.name_prefix}-emr-ec2-profile"
  role = aws_iam_role.emr_ec2.name
}

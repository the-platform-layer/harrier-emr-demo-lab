locals {
  raw_bucket_name       = "${local.name_prefix}-raw-${random_id.suffix.hex}"
  processed_bucket_name = "${local.name_prefix}-processed-${random_id.suffix.hex}"
  logs_bucket_name      = "${local.name_prefix}-logs-${random_id.suffix.hex}"
}

resource "aws_s3_bucket" "raw" {
  bucket        = local.raw_bucket_name
  force_destroy = var.force_destroy_buckets

  tags = {
    Name        = local.raw_bucket_name
    DataPurpose = "raw-demo-input"
  }
}

resource "aws_s3_bucket" "processed" {
  bucket        = local.processed_bucket_name
  force_destroy = var.force_destroy_buckets

  tags = {
    Name        = local.processed_bucket_name
    DataPurpose = "processed-demo-output"
  }
}

resource "aws_s3_bucket" "logs" {
  bucket        = local.logs_bucket_name
  force_destroy = var.force_destroy_buckets

  tags = {
    Name        = local.logs_bucket_name
    DataPurpose = "emr-demo-logs"
  }
}

resource "aws_s3_bucket_public_access_block" "raw" {
  bucket                  = aws_s3_bucket.raw.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "processed" {
  bucket                  = aws_s3_bucket.processed.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "logs" {
  bucket                  = aws_s3_bucket.logs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "raw" {
  bucket = aws_s3_bucket.raw.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "processed" {
  bucket = aws_s3_bucket.processed.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "raw" {
  bucket = aws_s3_bucket.raw.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "processed" {
  bucket = aws_s3_bucket.processed.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "logs" {
  bucket = aws_s3_bucket.logs.id

  versioning_configuration {
    status = "Enabled"
  }
}

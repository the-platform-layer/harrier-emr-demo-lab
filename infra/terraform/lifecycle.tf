resource "aws_s3_bucket_lifecycle_configuration" "raw" {
  bucket = aws_s3_bucket.raw.id

  rule {
    id     = "expire-raw-demo-data"
    status = "Enabled"

    filter {
      prefix = ""
    }

    expiration {
      days = var.raw_data_retention_days
    }

    noncurrent_version_expiration {
      noncurrent_days = var.raw_data_retention_days
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "processed" {
  bucket = aws_s3_bucket.processed.id

  rule {
    id     = "expire-processed-demo-data"
    status = "Enabled"

    filter {
      prefix = ""
    }

    expiration {
      days = var.processed_data_retention_days
    }

    noncurrent_version_expiration {
      noncurrent_days = var.processed_data_retention_days
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    id     = "expire-emr-demo-logs"
    status = "Enabled"

    filter {
      prefix = ""
    }

    expiration {
      days = var.emr_log_retention_days
    }

    noncurrent_version_expiration {
      noncurrent_days = var.emr_log_retention_days
    }
  }
}

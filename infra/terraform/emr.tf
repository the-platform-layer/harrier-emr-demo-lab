resource "aws_emr_cluster" "demo" {
  name          = "${local.name_prefix}-emr-ec2"
  release_label = var.emr_release_label
  applications  = ["Spark", "Livy"]

  service_role = aws_iam_role.emr_service.arn
  log_uri      = "s3://${aws_s3_bucket.logs.bucket}/emr/"

  keep_job_flow_alive_when_no_steps = true
  termination_protection            = false
  scale_down_behavior               = "TERMINATE_AT_TASK_COMPLETION"

  configurations_json = jsonencode([
    {
      Classification = "spark-defaults"
      Properties = {
        "spark.eventLog.enabled"        = "true"
        "spark.eventLog.dir"            = "s3://${aws_s3_bucket.logs.bucket}/spark-event-logs/"
        "spark.history.fs.logDirectory" = "s3://${aws_s3_bucket.logs.bucket}/spark-event-logs/"
      }
    }
  ])

  ec2_attributes {
    subnet_id                         = aws_subnet.public.id
    instance_profile                  = aws_iam_instance_profile.emr_ec2.arn
    emr_managed_master_security_group = aws_security_group.emr_master.id
    emr_managed_slave_security_group  = aws_security_group.emr_core.id
  }

  master_instance_group {
    name           = "Primary"
    instance_type  = var.master_instance_type
    instance_count = 1

    ebs_config {
      size                 = var.ebs_volume_size_gb
      type                 = "gp3"
      volumes_per_instance = 1
    }
  }

  core_instance_group {
    name           = "Core"
    instance_type  = var.core_instance_type
    instance_count = var.core_instance_count

    ebs_config {
      size                 = var.ebs_volume_size_gb
      type                 = "gp3"
      volumes_per_instance = 1
    }
  }

  auto_termination_policy {
    idle_timeout = var.max_runtime_hours * 3600
  }

  tags = {
    Name = "${local.name_prefix}-emr-ec2"
  }

  depends_on = [
    aws_iam_role_policy_attachment.emr_service_managed,
    aws_iam_role_policy_attachment.emr_ec2_managed,
    aws_iam_role_policy.emr_ec2_s3_access,
    aws_s3_bucket_lifecycle_configuration.logs,
  ]
}

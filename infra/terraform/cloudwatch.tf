resource "aws_cloudwatch_log_group" "demo" {
  name              = "/${local.name_prefix}/demo"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = {
    Name = "${local.name_prefix}-demo-log-group"
  }
}

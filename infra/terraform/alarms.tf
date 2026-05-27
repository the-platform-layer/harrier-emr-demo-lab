resource "aws_cloudwatch_metric_alarm" "emr_cluster_idle" {
  alarm_name          = "${local.name_prefix}-emr-cluster-idle"
  alarm_description   = "Demo alarm showing the EMR cluster has been idle. Auto-termination should also be enabled."
  namespace           = "AWS/ElasticMapReduce"
  metric_name         = "IsIdle"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 3
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  actions_enabled     = false

  dimensions = {
    JobFlowId = aws_emr_cluster.demo.id
  }

  tags = {
    Name = "${local.name_prefix}-emr-cluster-idle"
  }
}

resource "aws_cloudwatch_metric_alarm" "emr_apps_failed" {
  alarm_name          = "${local.name_prefix}-emr-apps-failed"
  alarm_description   = "Demo alarm placeholder for failed YARN/Spark applications."
  namespace           = "AWS/ElasticMapReduce"
  metric_name         = "AppsFailed"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  actions_enabled     = false

  dimensions = {
    JobFlowId = aws_emr_cluster.demo.id
  }

  tags = {
    Name = "${local.name_prefix}-emr-apps-failed"
  }
}

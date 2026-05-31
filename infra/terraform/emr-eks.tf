resource "aws_cloudwatch_log_group" "emr_eks" {
  name              = "/${local.name_prefix}/emr-eks"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = {
    Name = "${local.name_prefix}-emr-eks-log-group"
  }
}

resource "aws_emrcontainers_virtual_cluster" "demo" {
  count = var.enable_emr_eks ? 1 : 0

  name = "${local.name_prefix}-emr-eks"

  container_provider {
    id   = var.emr_eks_cluster_name
    type = "EKS"

    info {
      eks_info {
        namespace = var.emr_eks_namespace
      }
    }
  }

  tags = {
    Name = "${local.name_prefix}-emr-eks"
  }

  lifecycle {
    precondition {
      condition     = length(trimspace(var.emr_eks_cluster_name)) > 0
      error_message = "emr_eks_cluster_name is required when enable_emr_eks is true."
    }
  }
}

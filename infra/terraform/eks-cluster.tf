locals {
  demo_eks_cluster_name = (
    length(trimspace(var.demo_eks_cluster_name)) > 0
    ? trimspace(var.demo_eks_cluster_name)
    : "${local.name_prefix}-eks"
  )
  emr_eks_cluster_name_effective = (
    var.enable_demo_eks_cluster
    ? local.demo_eks_cluster_name
    : var.emr_eks_cluster_name
  )
  create_emr_eks_job_role = (
    var.enable_demo_eks_cluster
    || (var.enable_emr_eks && length(trimspace(var.emr_eks_job_role_arn)) == 0)
  )
  emr_eks_job_role_arn_effective = (
    length(trimspace(var.emr_eks_job_role_arn)) > 0
    ? var.emr_eks_job_role_arn
    : try(aws_iam_role.emr_eks_job[0].arn, "")
  )
}

data "aws_iam_policy_document" "eks_cluster_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["eks.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "eks_node_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "eks_cluster" {
  count = var.enable_demo_eks_cluster ? 1 : 0

  name               = "${local.name_prefix}-eks-cluster-role"
  assume_role_policy = data.aws_iam_policy_document.eks_cluster_assume_role.json

  tags = {
    Name = "${local.name_prefix}-eks-cluster-role"
  }
}

resource "aws_iam_role_policy_attachment" "eks_cluster" {
  count = var.enable_demo_eks_cluster ? 1 : 0

  role       = aws_iam_role.eks_cluster[0].name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonEKSClusterPolicy"
}

resource "aws_iam_role" "eks_node" {
  count = var.enable_demo_eks_cluster ? 1 : 0

  name               = "${local.name_prefix}-eks-node-role"
  assume_role_policy = data.aws_iam_policy_document.eks_node_assume_role.json

  tags = {
    Name = "${local.name_prefix}-eks-node-role"
  }
}

resource "aws_iam_role_policy_attachment" "eks_node_worker" {
  count = var.enable_demo_eks_cluster ? 1 : 0

  role       = aws_iam_role.eks_node[0].name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonEKSWorkerNodePolicy"
}

resource "aws_iam_role_policy_attachment" "eks_node_cni" {
  count = var.enable_demo_eks_cluster ? 1 : 0

  role       = aws_iam_role.eks_node[0].name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonEKS_CNI_Policy"
}

resource "aws_iam_role_policy_attachment" "eks_node_ecr" {
  count = var.enable_demo_eks_cluster ? 1 : 0

  role       = aws_iam_role.eks_node[0].name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_eks_cluster" "demo" {
  count = var.enable_demo_eks_cluster ? 1 : 0

  name     = local.demo_eks_cluster_name
  role_arn = aws_iam_role.eks_cluster[0].arn
  version  = length(trimspace(var.demo_eks_kubernetes_version)) > 0 ? var.demo_eks_kubernetes_version : null

  access_config {
    authentication_mode                         = "API_AND_CONFIG_MAP"
    bootstrap_cluster_creator_admin_permissions = true
  }

  vpc_config {
    subnet_ids              = [aws_subnet.public.id, aws_subnet.public_secondary.id]
    endpoint_private_access = false
    endpoint_public_access  = true
  }

  tags = {
    Name = local.demo_eks_cluster_name
  }

  depends_on = [aws_iam_role_policy_attachment.eks_cluster]
}

data "tls_certificate" "eks_oidc" {
  count = var.enable_demo_eks_cluster ? 1 : 0

  url = aws_eks_cluster.demo[0].identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "eks" {
  count = var.enable_demo_eks_cluster ? 1 : 0

  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks_oidc[0].certificates[0].sha1_fingerprint]
  url             = aws_eks_cluster.demo[0].identity[0].oidc[0].issuer

  tags = {
    Name = "${local.name_prefix}-eks-oidc"
  }
}

resource "aws_eks_node_group" "demo" {
  count = var.enable_demo_eks_cluster ? 1 : 0

  cluster_name    = aws_eks_cluster.demo[0].name
  node_group_name = "${local.name_prefix}-eks-workers"
  node_role_arn   = aws_iam_role.eks_node[0].arn
  subnet_ids      = [aws_subnet.public.id, aws_subnet.public_secondary.id]
  capacity_type   = "ON_DEMAND"
  disk_size       = 50
  instance_types  = var.demo_eks_node_instance_types

  scaling_config {
    desired_size = var.demo_eks_node_desired_size
    max_size     = var.demo_eks_node_max_size
    min_size     = var.demo_eks_node_min_size
  }

  update_config {
    max_unavailable = 1
  }

  tags = {
    Name = "${local.name_prefix}-eks-workers"
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_node_worker,
    aws_iam_role_policy_attachment.eks_node_cni,
    aws_iam_role_policy_attachment.eks_node_ecr,
  ]
}

data "aws_iam_policy_document" "emr_eks_job_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["elasticmapreduce.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "emr_eks_job" {
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
    sid       = "DescribeCloudWatchLogGroups"
    actions   = ["logs:DescribeLogGroups"]
    resources = ["*"]
  }

  statement {
    sid = "WriteCloudWatchLogStreams"
    actions = [
      "logs:CreateLogStream",
      "logs:DescribeLogStreams",
      "logs:PutLogEvents",
    ]
    resources = [
      aws_cloudwatch_log_group.emr_eks.arn,
      "${aws_cloudwatch_log_group.emr_eks.arn}:*",
    ]
  }
}

resource "aws_iam_role" "emr_eks_job" {
  count = local.create_emr_eks_job_role ? 1 : 0

  name               = "${local.name_prefix}-emr-eks-job-role"
  assume_role_policy = data.aws_iam_policy_document.emr_eks_job_assume_role.json

  tags = {
    Name = "${local.name_prefix}-emr-eks-job-role"
  }
}

resource "aws_iam_role_policy" "emr_eks_job" {
  count = local.create_emr_eks_job_role ? 1 : 0

  name   = "${local.name_prefix}-emr-eks-job"
  role   = aws_iam_role.emr_eks_job[0].id
  policy = data.aws_iam_policy_document.emr_eks_job.json
}

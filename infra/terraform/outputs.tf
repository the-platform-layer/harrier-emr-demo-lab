output "project" {
  value = local.project
}

output "region" {
  value = var.region
}

output "max_runtime_hours" {
  value = var.max_runtime_hours
}

output "cluster_id" {
  value = aws_emr_cluster.demo.id
}

output "log_uri" {
  value = aws_emr_cluster.demo.log_uri
}

output "raw_bucket" {
  value = aws_s3_bucket.raw.bucket
}

output "processed_bucket" {
  value = aws_s3_bucket.processed.bucket
}

output "logs_bucket" {
  value = aws_s3_bucket.logs.bucket
}

output "vpc_id" {
  value = aws_vpc.demo.id
}

output "public_subnet_id" {
  value = aws_subnet.public.id
}

output "emr_service_role_arn" {
  value = aws_iam_role.emr_service.arn
}

output "emr_ec2_instance_profile_arn" {
  value = aws_iam_instance_profile.emr_ec2.arn
}

output "budget_setup_note" {
  value = local.budget_setup_note
}

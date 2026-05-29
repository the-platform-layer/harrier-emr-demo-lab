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

output "public_secondary_subnet_id" {
  value = aws_subnet.public_secondary.id
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

output "mwaa_ecr_repository_url" {
  value = aws_ecr_repository.mwaa_local_runner.repository_url
}

output "mwaa_airflow_url" {
  value = "http://${aws_lb.mwaa.dns_name}:${var.mwaa_alb_port}"
}

output "mwaa_ecs_cluster" {
  value = aws_ecs_cluster.mwaa.name
}

output "mwaa_ecs_service" {
  value = aws_ecs_service.mwaa.name
}

output "mwaa_admin_username" {
  value = "admin"
}

output "mwaa_admin_password_secret_arn" {
  value = aws_secretsmanager_secret.mwaa_admin_password.arn
}

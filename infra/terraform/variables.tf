variable "region" {
  description = "AWS region for the disposable demo lab."
  type        = string
  default     = "ap-southeast-2"
}

variable "name_prefix" {
  description = "Prefix for every named demo resource."
  type        = string
  default     = "harrier-demo"
}

variable "max_runtime_hours" {
  description = "Idle timeout window for EMR auto-termination. This is not a hard wall-clock runtime cap if jobs keep the cluster busy."
  type        = number
  default     = 4

  validation {
    condition     = var.max_runtime_hours >= 1 && var.max_runtime_hours <= 24
    error_message = "max_runtime_hours must be between 1 and 24 for the disposable demo lab."
  }
}

variable "enable_db_scenarios" {
  description = "Enable optional RDS/PostgreSQL demo resources in later slices."
  type        = bool
  default     = false
}

variable "vpc_cidr" {
  description = "CIDR block for the demo VPC."
  type        = string
  default     = "10.42.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block for the public EMR subnet."
  type        = string
  default     = "10.42.10.0/24"
}

variable "public_subnet_secondary_cidr" {
  description = "CIDR block for the secondary public subnet used by the MWAA local runner ALB."
  type        = string
  default     = "10.42.11.0/24"
}

variable "availability_zone" {
  description = "Optional availability zone for the demo subnet. Defaults to the first available zone."
  type        = string
  default     = null
}

variable "secondary_availability_zone" {
  description = "Optional secondary availability zone for ALB-backed demo services. Defaults to the second available zone."
  type        = string
  default     = null
}

variable "emr_release_label" {
  description = "EMR release label for the demo cluster."
  type        = string
  default     = "emr-6.15.0"
}

variable "emr_serverless_release_label" {
  description = "EMR release label for the demo EMR Serverless Spark application."
  type        = string
  default     = "emr-7.2.0"
}

variable "emr_serverless_idle_timeout_minutes" {
  description = "Idle auto-stop timeout for the demo EMR Serverless application."
  type        = number
  default     = 15

  validation {
    condition     = var.emr_serverless_idle_timeout_minutes >= 1 && var.emr_serverless_idle_timeout_minutes <= 60
    error_message = "emr_serverless_idle_timeout_minutes must be between 1 and 60 for the disposable demo lab."
  }
}

variable "emr_serverless_max_cpu" {
  description = "Maximum CPU capacity for the demo EMR Serverless application."
  type        = string
  default     = "4 vCPU"
}

variable "emr_serverless_max_memory" {
  description = "Maximum memory capacity for the demo EMR Serverless application."
  type        = string
  default     = "16 GB"
}

variable "emr_serverless_max_disk" {
  description = "Maximum disk capacity for the demo EMR Serverless application."
  type        = string
  default     = "100 GB"
}

variable "enable_emr_eks" {
  description = "Register an existing EKS namespace as an EMR on EKS virtual cluster for Slice 31."
  type        = bool
  default     = false
}

variable "emr_eks_cluster_name" {
  description = "Existing EKS cluster name to register with EMR on EKS when enable_emr_eks is true."
  type        = string
  default     = ""
}

variable "emr_eks_namespace" {
  description = "Kubernetes namespace used for EMR on EKS demo job runs."
  type        = string
  default     = "harrier-emr-jobs"
}

variable "emr_eks_release_label" {
  description = "EMR release label for demo EMR on EKS job runs."
  type        = string
  default     = "emr-7.2.0-latest"
}

variable "emr_eks_job_role_arn" {
  description = "IAM role ARN onboarded for EMR on EKS job execution."
  type        = string
  default     = ""
}

variable "emr_eks_bad_image_uri" {
  description = "Deliberately invalid Spark image URI used by the image_pull_failure scenario."
  type        = string
  default     = "public.ecr.aws/docker/library/busybox:not-a-real-harrier-demo-tag"
}

variable "master_instance_type" {
  description = "Instance type for the EMR primary node."
  type        = string
  default     = "m5.xlarge"
}

variable "core_instance_type" {
  description = "Instance type for EMR core nodes."
  type        = string
  default     = "m5.xlarge"
}

variable "core_instance_count" {
  description = "Number of EMR core nodes."
  type        = number
  default     = 1

  validation {
    condition     = var.core_instance_count >= 1 && var.core_instance_count <= 3
    error_message = "core_instance_count must be between 1 and 3 for this demo lab."
  }
}

variable "ebs_volume_size_gb" {
  description = "EBS volume size for EMR nodes."
  type        = number
  default     = 32
}

variable "raw_data_retention_days" {
  description = "Retention period for raw demo data."
  type        = number
  default     = 7
}

variable "processed_data_retention_days" {
  description = "Retention period for processed demo output."
  type        = number
  default     = 7
}

variable "emr_log_retention_days" {
  description = "Retention period for archived EMR/Spark logs in S3."
  type        = number
  default     = 14
}

variable "cloudwatch_log_retention_days" {
  description = "Retention period for demo CloudWatch log groups."
  type        = number
  default     = 14
}

variable "force_destroy_buckets" {
  description = "Allow Terraform destroy to remove non-empty demo buckets."
  type        = bool
  default     = true
}

variable "monthly_budget_limit_usd" {
  description = "Suggested monthly demo budget threshold used in documentation."
  type        = number
  default     = 100
}

variable "mwaa_image_tag" {
  description = "Image tag to run for the Harrier MWAA local runner ECS service."
  type        = string
  default     = "latest"
}

variable "mwaa_desired_count" {
  description = "Number of MWAA local runner ECS tasks. Defaults to 0 so baseline Terraform can apply before an image is pushed."
  type        = number
  default     = 0
}

variable "mwaa_task_cpu" {
  description = "CPU units for the MWAA local runner ECS task."
  type        = number
  default     = 1024
}

variable "mwaa_task_memory" {
  description = "Memory in MiB for the MWAA local runner ECS task."
  type        = number
  default     = 4096
}

variable "mwaa_alb_port" {
  description = "Public ALB listener port for the MWAA local runner Airflow UI."
  type        = number
  default     = 8080
}

variable "mwaa_web_allowed_cidrs" {
  description = "CIDR blocks allowed to reach the MWAA local runner Airflow UI."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

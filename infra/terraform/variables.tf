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

variable "availability_zone" {
  description = "Optional availability zone for the demo subnet. Defaults to the first available zone."
  type        = string
  default     = null
}

variable "emr_release_label" {
  description = "EMR release label for the demo cluster."
  type        = string
  default     = "emr-6.15.0"
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

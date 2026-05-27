variable "region" {
  type    = string
  default = "ap-southeast-2"
}

variable "max_runtime_hours" {
  type    = number
  default = 4
}

variable "enable_db_scenarios" {
  type    = bool
  default = false
}


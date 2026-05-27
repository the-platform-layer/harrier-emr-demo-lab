terraform {
  required_version = ">= 1.6.0"
}

locals {
  project = "harrier-demo"
  tags = {
    Project     = "harrier-demo"
    Environment = "demo"
  }
}


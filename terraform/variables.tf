variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "CIDR for AWS VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "environment" {
  description = "stage of cloud environment"
  type        = string
  default     = "dev"
}
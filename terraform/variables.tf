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

variable "instance_type" {
  description = "ec2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "key_pair_name" {
  description = "Existing AWS key pair name"
}

variable "ssh_allowed_cidr" {
  description = "CIDR block allowed to SSH into the instance"
  type        = string
  default     = "0.0.0.0/0"
}

variable "github_repository" {
  description = "GitHub repository allowed to assume the deploy role (owner/name)"
  type        = string
  default     = "richard-romero/secure-cloud-platform"
}

variable "github_environment" {
  description = "GitHub Actions environment name allowed to assume the deploy role"
  type        = string
  default     = "production"
}
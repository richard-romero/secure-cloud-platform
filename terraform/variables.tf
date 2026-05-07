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
  default     = "t4g.micro"
}

variable "key_pair_name" {
  description = "Existing AWS key pair name"
}

variable "ssh_allowed_cidr" {
  description = "CIDR block allowed to SSH into the instance"
  type        = string
  default     = "0.0.0.0/0"
}
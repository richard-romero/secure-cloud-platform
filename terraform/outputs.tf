output "configured_region" {
  description = "region configured for terraform resources"
  value = var.aws_region
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "public_subnet_id" {
  description = "Public subnet ID"
  value = aws_subnet.public.id
}

output "private_subnet_id" {
  description = "Private subnet ID"
  value = aws_subnet.private.id
}
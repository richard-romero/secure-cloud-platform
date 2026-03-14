output "configured_region" {
  value = var.aws_region
}

output "vpc_id" {
  description = "ID of the created VPC"
  value       = aws_vpc.main.id
}
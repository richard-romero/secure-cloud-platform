output "configured_region" {
  description = "region configured for terraform resources"
  value       = var.aws_region
}

output "vpc_id" {
  value = aws_vpc.main.id
}

output "public_subnet_id" {
  value = aws_subnet.public.id
}

output "private_subnet_id" {
  value = aws_subnet.private.id
}

output "security_group_id" {
  value = aws_security_group.web_sg.id
}

output "instance_profile_name" {
  value = aws_iam_instance_profile.ec2_profile.name
}

output "instance_public_ip" {
  value = aws_instance.web.public_ip
}

output "instance_id" {
  value = aws_instance.web.id
}

output "ssh_command" {
  value = "ssh -i ~/.ssh/${var.key_pair_name} ec2-user@${aws_instance.web.public_ip}"
}

output "github_actions_role_arn" {
  description = "IAM role ARN for GitHub Actions OIDC deploy job (set as AWS_ROLE_ARN in the production environment)"
  value       = aws_iam_role.github_actions_deploy.arn
}
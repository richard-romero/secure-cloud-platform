#!/bin/bash
set -eux

# Register with SSM first so the instance is manageable even if later steps fail.
dnf install -y amazon-ssm-agent
systemctl enable amazon-ssm-agent
systemctl start amazon-ssm-agent

dnf install -y nano git docker amazon-cloudwatch-agent

systemctl enable docker
systemctl start docker

usermod -aG docker ec2-user

systemctl enable amazon-cloudwatch-agent
systemctl start amazon-cloudwatch-agent

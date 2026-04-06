#!/bin/bash
set -eux

# Update system
dnf update -y

# Utilities
dnf install -y nano git docker amazon-cloudwatch-agent

systemctl enable docker
systemctl start docker

usermod -aG docker ec2-user

systemctl enable amazon-cloudwatch-agent
systemctl start amazon-cloudwatch-agent
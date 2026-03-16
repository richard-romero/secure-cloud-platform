resource "aws_vpc" "main" {
  cidr_block = var.vpc_cidr

  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name        = "terraform-vpc"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_subnet" "public" {
  vpc_id = aws_vpc.main.id

  cidr_block = "10.0.1.0/24"

  availability_zone = "us-east-1a"

  map_public_ip_on_launch = true

  tags = {
    Name        = "public-subnet"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_subnet" "private" {
  vpc_id = aws_vpc.main.id

  cidr_block = "10.0.2.0/24"

  availability_zone = "us-east-1a"

  map_public_ip_on_launch = false

  tags = {
    Name        = "private-subnet"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
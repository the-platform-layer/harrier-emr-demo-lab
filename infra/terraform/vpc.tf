resource "aws_vpc" "demo" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${local.name_prefix}-vpc"
  }
}

resource "aws_internet_gateway" "demo" {
  vpc_id = aws_vpc.demo.id

  tags = {
    Name = "${local.name_prefix}-igw"
  }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.demo.id
  cidr_block              = var.public_subnet_cidr
  availability_zone       = coalesce(var.availability_zone, data.aws_availability_zones.available.names[0])
  map_public_ip_on_launch = true

  tags = {
    Name = "${local.name_prefix}-public-subnet"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.demo.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.demo.id
  }

  tags = {
    Name = "${local.name_prefix}-public-rt"
  }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "emr_master" {
  name        = "${local.name_prefix}-emr-master"
  description = "Demo EMR primary node security group"
  vpc_id      = aws_vpc.demo.id

  tags = {
    Name = "${local.name_prefix}-emr-master"
  }
}

resource "aws_security_group" "emr_core" {
  name        = "${local.name_prefix}-emr-core"
  description = "Demo EMR core node security group"
  vpc_id      = aws_vpc.demo.id

  tags = {
    Name = "${local.name_prefix}-emr-core"
  }
}

resource "aws_security_group_rule" "master_from_master" {
  type              = "ingress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  security_group_id = aws_security_group.emr_master.id
  self              = true
}

resource "aws_security_group_rule" "master_from_core" {
  type                     = "ingress"
  from_port                = 0
  to_port                  = 0
  protocol                 = "-1"
  security_group_id        = aws_security_group.emr_master.id
  source_security_group_id = aws_security_group.emr_core.id
}

resource "aws_security_group_rule" "core_from_core" {
  type              = "ingress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  security_group_id = aws_security_group.emr_core.id
  self              = true
}

resource "aws_security_group_rule" "core_from_master" {
  type                     = "ingress"
  from_port                = 0
  to_port                  = 0
  protocol                 = "-1"
  security_group_id        = aws_security_group.emr_core.id
  source_security_group_id = aws_security_group.emr_master.id
}

resource "aws_security_group_rule" "master_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.emr_master.id
}

resource "aws_security_group_rule" "core_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.emr_core.id
}

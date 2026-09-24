data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  name = "${var.cluster_name}-${var.environment}"

  azs = slice(data.aws_availability_zones.available.names, 0, 2)

  tags = {
    Project     = "KubePilot"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "6.7.2"

  name = "${local.name}-vpc"
  cidr = "10.0.0.0/16"

  azs = local.azs

  private_subnets = [
    "10.0.1.0/24",
    "10.0.2.0/24"
  ]

  public_subnets = [
    "10.0.101.0/24",
    "10.0.102.0/24"
  ]

  enable_nat_gateway      = false
  single_nat_gateway      = false
  map_public_ip_on_launch = true

  enable_dns_hostnames = true
  enable_dns_support   = true

  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
  }

  tags = local.tags
}
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 21.0"

  name               = local.name
  kubernetes_version = "1.33"

  endpoint_public_access       = true
  endpoint_public_access_cidrs = ["196.115.105.32/32"]

  enable_cluster_creator_admin_permissions = true

  addons = {
    coredns = {}

    kube-proxy = {}

    vpc-cni = {
      before_compute = true
    }

    eks-pod-identity-agent = {
      before_compute = true
    }
  }

  vpc_id = module.vpc.vpc_id

  # Dev/lab: public subnets to avoid NAT Gateway cost.
  subnet_ids = module.vpc.public_subnets

  eks_managed_node_groups = {
    kubepilot = {
      ami_type = "AL2023_x86_64_STANDARD"

      instance_types = ["t3.small"]

      min_size     = 3
      max_size     = 3
      desired_size = 3
    }
  }

  tags = local.tags
}

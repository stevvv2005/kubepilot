variable "aws_region" {
  description = "AWS region used by KubePilot"
  type        = string
  default     = "eu-west-3"
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "kubepilot-eks"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}
terraform {
# setup backend here
#  backend "s3" {
#     bucket = "mybucket"
#     key    = "path/to/my/key"
#     region = "us-east-1"
#   }
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

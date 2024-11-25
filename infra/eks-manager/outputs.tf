output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.lambda_repo.repository_url
}

output "lambda_function_arn" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.eks_manager.arn
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.eks_manager.function_name
}

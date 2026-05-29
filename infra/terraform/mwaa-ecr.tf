resource "aws_ecr_repository" "mwaa_local_runner" {
  name         = "${local.name_prefix}-mwaa-local-runner"
  force_delete = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${local.name_prefix}-mwaa-local-runner"
  }
}

resource "aws_ecr_lifecycle_policy" "mwaa_local_runner" {
  repository = aws_ecr_repository.mwaa_local_runner.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep the latest 10 MWAA local runner images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

resource "random_password" "mwaa_admin_password" {
  length  = 20
  special = false
}

resource "aws_secretsmanager_secret" "mwaa_admin_password" {
  name        = "${local.name_prefix}/mwaa/admin-password"
  description = "Demo Airflow admin password for the Harrier MWAA local runner."

  tags = {
    Name = "${local.name_prefix}-mwaa-admin-password"
  }
}

resource "aws_secretsmanager_secret_version" "mwaa_admin_password" {
  secret_id     = aws_secretsmanager_secret.mwaa_admin_password.id
  secret_string = random_password.mwaa_admin_password.result
}

resource "aws_ecs_cluster" "mwaa" {
  name = "${local.name_prefix}-mwaa-local-runner"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "${local.name_prefix}-mwaa-local-runner"
  }
}

resource "aws_cloudwatch_log_group" "mwaa" {
  name              = "/ecs/${local.name_prefix}-mwaa-local-runner"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = {
    Name = "${local.name_prefix}-mwaa-local-runner"
  }
}

resource "aws_security_group" "mwaa_alb" {
  name        = "${local.name_prefix}-mwaa-alb"
  description = "Public ALB for the Harrier MWAA local runner demo UI"
  vpc_id      = aws_vpc.demo.id

  ingress {
    from_port   = var.mwaa_alb_port
    to_port     = var.mwaa_alb_port
    protocol    = "tcp"
    cidr_blocks = var.mwaa_web_allowed_cidrs
    description = "Airflow web UI"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow outbound"
  }

  tags = {
    Name = "${local.name_prefix}-mwaa-alb"
  }
}

resource "aws_security_group" "mwaa_tasks" {
  name        = "${local.name_prefix}-mwaa-tasks"
  description = "Fargate tasks for the Harrier MWAA local runner demo"
  vpc_id      = aws_vpc.demo.id

  ingress {
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.mwaa_alb.id]
    description     = "Airflow webserver from ALB"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "AWS API and internet egress"
  }

  tags = {
    Name = "${local.name_prefix}-mwaa-tasks"
  }
}

resource "aws_lb" "mwaa" {
  name               = "${local.name_prefix}-mwaa"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.mwaa_alb.id]
  subnets            = [aws_subnet.public.id, aws_subnet.public_secondary.id]

  tags = {
    Name = "${local.name_prefix}-mwaa"
  }
}

resource "aws_lb_target_group" "mwaa" {
  name        = "${local.name_prefix}-mwaa"
  port        = 8080
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = aws_vpc.demo.id

  health_check {
    enabled             = true
    path                = "/health"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 5
  }

  tags = {
    Name = "${local.name_prefix}-mwaa"
  }
}

resource "aws_lb_listener" "mwaa" {
  load_balancer_arn = aws_lb.mwaa.arn
  port              = var.mwaa_alb_port
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.mwaa.arn
  }
}

resource "aws_ecs_task_definition" "mwaa" {
  family                   = "${local.name_prefix}-mwaa-local-runner"
  cpu                      = var.mwaa_task_cpu
  memory                   = var.mwaa_task_memory
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  execution_role_arn       = aws_iam_role.mwaa_execution.arn
  task_role_arn            = aws_iam_role.mwaa_task.arn

  container_definitions = jsonencode([
    {
      name      = "mwaa-local-runner"
      image     = "${aws_ecr_repository.mwaa_local_runner.repository_url}:${var.mwaa_image_tag}"
      essential = true

      portMappings = [
        {
          containerPort = 8080
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "AIRFLOW__CORE__EXECUTOR", value = "SequentialExecutor" },
        { name = "AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION", value = "False" },
        { name = "AIRFLOW__API__AUTH_BACKENDS", value = "airflow.api.auth.backend.basic_auth,airflow.api.auth.backend.session" },
        { name = "AIRFLOW__WEBSERVER__BASE_URL", value = "http://${aws_lb.mwaa.dns_name}:${var.mwaa_alb_port}" },
        { name = "AWS_REGION", value = var.region },
        { name = "AWS_DEFAULT_REGION", value = var.region },
        { name = "CLUSTER_ID", value = aws_emr_cluster.demo.id },
        { name = "RAW_BUCKET", value = aws_s3_bucket.raw.bucket },
        { name = "PROCESSED_BUCKET", value = aws_s3_bucket.processed.bucket },
        { name = "LOGS_BUCKET", value = aws_s3_bucket.logs.bucket },
        { name = "LOG_URI", value = aws_emr_cluster.demo.log_uri },
        { name = "HARRIER_DEMO_REPO", value = "/usr/local/airflow/harrier-demo-lab" },
        { name = "PYTHONUNBUFFERED", value = "1" },
      ]

      secrets = [
        {
          name      = "DEFAULT_PASSWORD"
          valueFrom = aws_secretsmanager_secret.mwaa_admin_password.arn
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.mwaa.name
          awslogs-region        = var.region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])

  tags = {
    Name = "${local.name_prefix}-mwaa-local-runner"
  }
}

resource "aws_ecs_service" "mwaa" {
  name            = "${local.name_prefix}-mwaa-local-runner"
  cluster         = aws_ecs_cluster.mwaa.id
  task_definition = aws_ecs_task_definition.mwaa.arn
  desired_count   = var.mwaa_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = [aws_subnet.public.id]
    security_groups  = [aws_security_group.mwaa_tasks.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.mwaa.arn
    container_name   = "mwaa-local-runner"
    container_port   = 8080
  }

  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = var.mwaa_desired_count > 0 ? 100 : 0

  depends_on = [aws_lb_listener.mwaa]

  tags = {
    Name = "${local.name_prefix}-mwaa-local-runner"
  }
}

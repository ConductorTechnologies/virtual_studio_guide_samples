resource "aws_iam_role_policy_attachment" "cloudwatch_logs" {
  role       = var.iam_role_name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_ecs_task_definition" "this" {
  family                   = var.name
  execution_role_arn       = var.iam_role_arn
  task_role_arn            = var.task_role_arn
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = lookup(var.config, "cpu", null)
  memory                   = lookup(var.config, "memory", null)
  container_definitions    = var.container_definitions

  dynamic "volume" {
    for_each = var.efs_id != "" ? [var.efs_id] : []

    content {
      name = var.name

      efs_volume_configuration {
        file_system_id = volume.value
        root_directory = var.efs_root_dir
      }
    }
  }
}

resource "aws_ecs_service" "this" {
  name            = var.name
  cluster         = var.ecs_cluster_arn
  task_definition = aws_ecs_task_definition.this.arn
  desired_count   = lookup(var.config, "app_count", null)
  launch_type     = "FARGATE"

  network_configuration {
    assign_public_ip = lookup(var.config, "assign_public_ip", null)
    security_groups  = var.security_groups
    subnets          = var.subnets
  }

  dynamic "load_balancer" {
    for_each = var.target_group_arn != "" ? [var.target_group_arn] : []

    content {
      target_group_arn = load_balancer.value
      container_name   = lookup(var.config, "container_name", null)
      container_port   = lookup(var.config, "app_port", null)
    }
  }
}

resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/fargate/${aws_ecs_service.this.name}"
  retention_in_days = 14
}

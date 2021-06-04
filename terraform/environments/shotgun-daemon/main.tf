locals {
  bucket_name               = ""
  default_security_group_id = ""
  name                      = "shotgun-daemon"
  vpc_id                    = ""

  container_definitions = <<DEFINITION
  [
    {
      "name": "shotgun-daemon",
      "image": "",
      "environment": [
        {"name": "CONDUCTOR_API_KEY", "value": ""}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/aws/fargate/shotgun-daemon",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "fargate"
        }
      },
      "memoryReservation": 512,
      "mountPoints": [
        {
          "containerPath": "/mount/shotgun-daemon-efs",
          "sourceVolume": "shotgun-daemon"
        }
      ]
    }
  ] 
DEFINITION

  fargate_config = {
    cpu              = 256
    memory           = 512
    app_count        = 1
    assign_public_ip = false
    container_name   = "shotgun-daemon"
  }

  private_subnets = []
}

##############
# ECS Cluster
##############
module "ecs_cluster" {
  source = "../../modules/ecs-cluster"

  clusters = [local.name]
}

########################
# ECS Fargate Task Role
########################
module "execution_iam_role" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-assumable-role"
  version = "~> 2.22.0"

  trusted_role_services = [
    "ecs-tasks.amazonaws.com"
  ]

  create_role       = true
  role_name         = "${local.name}-role"
  role_requires_mfa = false
}

data "aws_iam_policy_document" "s3_access" {
  statement {
    actions = [
      "s3:*",
    ]

    resources = [
      "arn:aws:s3:::${local.bucket_name}/*",
    ]
  }
}

resource "aws_iam_policy" "s3_access" {
  name   = "${local.name}-s3-access"
  policy = data.aws_iam_policy_document.s3_access.json
}

module "task_iam_role" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-assumable-role"
  version = "~> 2.22.0"

  trusted_role_services = [
    "ecs.amazonaws.com",
    "ecs-tasks.amazonaws.com"
  ]

  create_role       = true
  role_name         = "${local.name}-task-role"
  role_requires_mfa = false
  custom_role_policy_arns = [
    aws_iam_policy.s3_access.arn
  ]
}

##############
# ECS Fargate
##############
module "fargate" {
  source = "../../modules/fargate"

  name         = local.name
  efs_id       = module.efs.id
  efs_root_dir = "/"

  iam_role_arn  = module.execution_iam_role.this_iam_role_arn
  iam_role_name = module.execution_iam_role.this_iam_role_name

  config                = local.fargate_config
  container_definitions = local.container_definitions
  ecs_cluster_arn       = module.ecs_cluster.cluster_arn[0]
  task_role_arn         = module.task_iam_role.this_iam_role_arn

  subnets = local.private_subnets
}

resource "aws_security_group" "efs" {
  name        = "${local.name}-efs"
  description = "${local.name} EFS"
  vpc_id      = local.vpc_id

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_security_group_rule" "efs_in" {
  description              = "Allow inbound NFS traffic from default security group"
  type                     = "ingress"
  from_port                = "2049"
  to_port                  = "2049"
  protocol                 = "tcp"
  source_security_group_id = local.default_security_group_id
  security_group_id        = aws_security_group.efs.id
}

resource "aws_security_group_rule" "efs_out" {
  description       = "Allow all outbound traffic from EFS"
  type              = "egress"
  cidr_blocks       = ["0.0.0.0/0"]
  from_port         = 0
  to_port           = 65535
  protocol          = "tcp"
  security_group_id = aws_security_group.efs.id
}

######
# EFS
######
module "efs" {
  source = "../../modules/efs"

  security_groups  = [aws_security_group.efs.id]
  subnet_ids       = local.private_subnets
  encrypted        = true
  transition_to_ia = "AFTER_7_DAYS"

  tags = {
    Name = "${local.name}-efs"
  }
}

variable "container_definitions" {
  description = "JSON formatted string containing a list of container definition maps for fargate service"
  type        = string
  # https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#container_definitions
}

variable "config" {
  description = "Map containing fargate configuration"
  type        = map(any)
}

variable "ecs_cluster_arn" {
  description = "The ARN of an ECS cluster on which the fargate service will run"
  type        = string
}

variable "efs_id" {
  description = "(Optional) The EFS ID to connect the fargate task to"
  type        = string
  default     = ""
}

variable "efs_root_dir" {
  description = "(Optional) The EFS root directory to mount"
  type        = string
  default     = ""
}

variable "environment" {
  description = "The Conductor environment"
  type        = string
  default     = "sandbox"
}

variable "iam_role_arn" {
  description = "The ARN of the IAM role for the fargate service to use."
  type        = string
}

variable "iam_role_name" {
  description = "The name of the IAM role for the fargate service to use."
  type        = string
}

variable "name" {
  description = "The name to assign to all created resources"
  type        = string
}

variable "region" {
  description = "The target AWS region"
  type        = string
  default     = "us-east-1"
}

variable "security_groups" {
  description = "The security groups associated with the fargate service. If you do not specify a security group, the default security group for the VPC is used."
  type        = list
  default     = []
}

variable "subnets" {
  description = "The (private) subnets associated with the fargate service"
  type        = list
}

variable "target_group_arn" {
  description = "The ARN of the target group onto which requests will be routed"
  type        = string
  default     = ""
}

variable "task_role_arn" {
  description = "The ARN of the IAM role that grants the ECS task access to AWS services"
  type        = string
  default     = null
}

variable "encrypted" {
  description = "(Optional) Set to True to encrypt the EFS."
  default     = false
  type        = bool
}

variable "subnet_ids" {
  description = "The subnets in which to place EFS mount points"
  type        = list
}

variable "security_groups" {
  description = "List of security groups to apply to EFS mount target"
  default     = []
  type        = list
}

variable "tags" {
  description = "A mapping of tags to assign to the resource."
  default     = {}
  type        = map(string)
}

variable "transition_to_ia" {
  description = "How long to wait before transition unused files to the IA storage class."
  default     = ""
  type        = string
}
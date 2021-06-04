resource "aws_efs_file_system" "this" {
  tags      = var.tags
  encrypted = var.encrypted

  dynamic "lifecycle_policy" {
    for_each = length(var.transition_to_ia) == 0 ? [] : [var.transition_to_ia]

    content {
      transition_to_ia = var.transition_to_ia
    }
  }
}

resource "aws_efs_mount_target" "this" {
  for_each = toset(var.subnet_ids)

  file_system_id  = aws_efs_file_system.this.id
  subnet_id       = each.value
  security_groups = var.security_groups
}

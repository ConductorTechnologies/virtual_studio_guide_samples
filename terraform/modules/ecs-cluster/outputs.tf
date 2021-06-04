output "cluster_arn" {
  value       = aws_ecs_cluster.cluster[*].arn
  description = "Cluster ARN"
}

output "cluster_id" {
  value       = aws_ecs_cluster.cluster[*].id
  description = "Cluster ID"
}

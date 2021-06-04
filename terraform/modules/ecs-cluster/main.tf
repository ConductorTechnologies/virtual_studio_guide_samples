resource "aws_ecs_cluster" "cluster" {
  count = length(var.clusters)

  name = var.clusters[count.index]
}

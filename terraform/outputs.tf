output "app_url" {
  description = "URL of the deployed application"
  value       = "http://localhost:${var.app_port}"
}

output "container_name" {
  description = "Name of the running container"
  value       = docker_container.staging.name
}

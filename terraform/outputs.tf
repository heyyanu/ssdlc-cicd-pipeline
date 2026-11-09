output "app_url" {
  description = "Staging application URL"
  value       = "http://localhost:8081"
}

output "container_name" {
  value = docker_container.staging.name
}


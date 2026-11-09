terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {}

# Use the Docker image built by the Jenkins pipeline
resource "docker_image" "app" {
  name         = "ssdlc-app:latest"
  keep_locally = true
}

# Deploy the application
resource "docker_container" "staging" {
  name  = "staging-app"
  image = docker_image.app.image_id

  ports {
    internal = 5000
    external = 8081
    ip       = "0.0.0.0"
  }

  restart = "on-failure"
}

output "app_url" {
  description = "Staging application URL"
  value       = "http://localhost:8081"
}

output "container_name" {
  value = docker_container.staging.name
}



terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {}

data "docker_image" "app" {
  name = "ssdlc-app:latest"
}

resource "docker_container" "staging" {
  name  = "staging-app"
  image = data.docker_image.app.id

  ports {
    internal = 5000
    external = 8081
    ip       = "0.0.0.0"
  }

  restart = "on-failure"
}

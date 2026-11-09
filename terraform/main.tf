terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {}

resource "docker_image" "app" {
  name         = "ssdlc-app:latest"
  keep_locally = true
}

resource "docker_container" "staging" {
  name  = "staging-app"
  image = docker_image.app.image_id

  ports {
    internal = 5000
    external = 5000
  }

  restart = "on-failure"
}

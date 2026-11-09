variable "app_name" {
  description = "Name of the application"
  type        = string
  default     = "ssdlc-app"
}

variable "app_port" {
  description = "Port the app runs on"
  type        = number
  default     = 5000
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "staging"
}

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "env" {
  description = "Environment name (dev or prod)"
  type        = string
}

variable "auth0_domain" {
  description = "Auth0 tenant domain"
  type        = string
}

variable "auth0_audience" {
  description = "Auth0 API audience"
  type        = string
}

variable "auth0_client_id" {
  description = "Auth0 client ID"
  type        = string
}

variable "backend_url" {
  description = "Public URL for the backend (used in frontend and OAuth callbacks)"
  type        = string
}

variable "frontend_url" {
  description = "Public URL for the frontend"
  type        = string
}

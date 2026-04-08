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

variable "auth0_client_secret" {
  description = "Auth0 client secret"
  type        = string
  sensitive   = true
}

variable "gemini_api_key" {
  description = "Gemini API key"
  type        = string
  sensitive   = true
}

variable "github_connection_name" {
  description = "Auth0 social connection name for GitHub (Auth0 Dashboard → Authentication → Social → GitHub → Name)"
  type        = string
  default     = "github"
}

variable "custom_domain_enabled" {
  description = "Enable Cloud Run custom domain mappings (requires domain verification in GCP)"
  type        = bool
  default     = false
}

variable "backend_custom_domain" {
  description = "Custom domain for backend (e.g. api-anon-skill-dev.evoa.one)"
  type        = string
  default     = ""
}

variable "frontend_custom_domain" {
  description = "Custom domain for frontend (e.g. anon-skill-dev.evoa.one)"
  type        = string
  default     = ""
}

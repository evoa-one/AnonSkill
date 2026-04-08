variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
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

variable "auth0_client_secret" {
  description = "Auth0 client secret"
  type        = string
  sensitive   = true
}

variable "backend_url" {
  description = "Public backend URL (Cloudflare custom domain or raw .run.app URL)"
  type        = string
}

variable "frontend_url" {
  description = "Public frontend URL (Cloudflare custom domain or raw .run.app URL)"
  type        = string
}

variable "gemini_api_key" {
  description = "Gemini API key"
  type        = string
  sensitive   = true
}

variable "initial_deploy" {
  description = "Set to true on first apply to use a placeholder image"
  type        = bool
  default     = false
}

variable "custom_domain_enabled" {
  description = "Enable Cloud Run custom domain mappings"
  type        = bool
  default     = false
}

variable "backend_custom_domain" {
  description = "Custom domain for backend"
  type        = string
  default     = ""
}

variable "frontend_custom_domain" {
  description = "Custom domain for frontend"
  type        = string
  default     = ""
}

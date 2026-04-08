terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  required_version = ">= 1.5"
}

provider "google" {
  project = var.project_id
  region  = var.region
}

module "anon_skill" {
  source = "../../modules/anon-skill"

  project_id      = var.project_id
  region          = var.region
  env             = "prod"
  auth0_domain    = var.auth0_domain
  auth0_audience  = var.auth0_audience
  auth0_client_id = var.auth0_client_id

  backend_url  = var.backend_url
  frontend_url = var.frontend_url

  auth0_client_secret = var.auth0_client_secret
  gemini_api_key      = var.gemini_api_key

  custom_domain_enabled  = var.custom_domain_enabled
  backend_custom_domain  = var.backend_custom_domain
  frontend_custom_domain = var.frontend_custom_domain
}

output "backend_cloud_run_url" {
  value = module.anon_skill.backend_cloud_run_url
}

output "frontend_cloud_run_url" {
  value = module.anon_skill.frontend_cloud_run_url
}

output "registry" {
  value = module.anon_skill.registry
}

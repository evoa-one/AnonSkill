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
  env             = "dev"
  auth0_domain    = var.auth0_domain
  auth0_audience  = var.auth0_audience
  auth0_client_id = var.auth0_client_id

  # Raw Cloud Run URLs are not known until after first apply.
  # After first apply, get them from outputs and set custom domains in Cloudflare.
  # For dev, we use the raw .run.app URLs directly (or map them in Cloudflare).
  backend_url  = var.backend_url
  frontend_url = var.frontend_url

  auth0_client_secret = var.auth0_client_secret
  gemini_api_key      = var.gemini_api_key
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

locals {
  name_prefix = "anon-skill-${var.env}"
  registry    = "${var.region}-docker.pkg.dev/${var.project_id}/anon-skill-${var.env}"
}

# ── Artifact Registry ─────────────────────────────────────────────────────────

resource "google_artifact_registry_repository" "main" {
  location      = var.region
  repository_id = "anon-skill-${var.env}"
  format        = "DOCKER"
}

# ── Cloud Run: Backend ────────────────────────────────────────────────────────

resource "google_cloud_run_v2_service" "backend" {
  name     = "${local.name_prefix}-backend"
  location = var.region

  template {
    containers {
      image = "${local.registry}/backend:latest"

      ports {
        container_port = 8000
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      env {
        name  = "auth0_domain"
        value = var.auth0_domain
      }
      env {
        name  = "auth0_audience"
        value = var.auth0_audience
      }
      env {
        name  = "auth0_client_id"
        value = var.auth0_client_id
      }
      env {
        name = "auth0_client_secret"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.auth0_client_secret.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "gemini_api_key"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemini_api_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name  = "callback_url"
        value = "${var.backend_url}/oauth/callback"
      }
      env {
        name  = "connect_callback_url"
        value = "${var.backend_url}/oauth/github/connect/callback"
      }
      env {
        name  = "frontend_url"
        value = var.frontend_url
      }
      env {
        name  = "github_connection_name"
        value = "github"
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }
  }
}

# ── Cloud Run: Frontend ───────────────────────────────────────────────────────

resource "google_cloud_run_v2_service" "frontend" {
  name     = "${local.name_prefix}-frontend"
  location = var.region

  template {
    containers {
      image = "${local.registry}/frontend:latest"

      ports {
        container_port = 3000
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }
  }
}

# ── Allow public access ───────────────────────────────────────────────────────

resource "google_cloud_run_v2_service_iam_member" "backend_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.backend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "frontend_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.frontend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ── Secret Manager ────────────────────────────────────────────────────────────

resource "google_secret_manager_secret" "auth0_client_secret" {
  secret_id = "${local.name_prefix}-auth0-client-secret"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "${local.name_prefix}-gemini-api-key"
  replication {
    auto {}
  }
}

data "google_compute_default_service_account" "default" {}

resource "google_secret_manager_secret_iam_member" "backend_auth0_secret" {
  secret_id = google_secret_manager_secret.auth0_client_secret.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${data.google_compute_default_service_account.default.email}"
}

resource "google_secret_manager_secret_iam_member" "backend_gemini_secret" {
  secret_id = google_secret_manager_secret.gemini_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${data.google_compute_default_service_account.default.email}"
}

output "backend_cloud_run_url" {
  description = "Raw Cloud Run URL for backend"
  value       = google_cloud_run_v2_service.backend.uri
}

output "frontend_cloud_run_url" {
  description = "Raw Cloud Run URL for frontend"
  value       = google_cloud_run_v2_service.frontend.uri
}

output "registry" {
  description = "Artifact Registry path"
  value       = local.registry
}

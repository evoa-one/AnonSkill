# Infrastructure

GCP infrastructure for AnonSkill, managed with Terraform.

## Structure

```
infra/
├── modules/anon-skill/     # Reusable module (Cloud Run, Artifact Registry, Secret Manager)
└── envs/
    ├── dev/                # Dev environment (separate registry, services, secrets)
    └── prod/               # Production environment
```

Each environment has its own Terraform state and GCP resources.

## Prerequisites

1. Install [Terraform](https://developer.hashicorp.com/terraform/install) (>= 1.5)
2. Install [gcloud CLI](https://cloud.google.com/sdk/docs/install)
3. Run the GCP init script to enable APIs and authenticate:
   ```bash
   ./scripts/gcp-init.sh YOUR_PROJECT_ID
   ```

## First Deploy

```bash
# 1. Set up tfvars
cp infra/envs/dev/terraform.tfvars.example infra/envs/dev/terraform.tfvars
# Fill in your values (Auth0 credentials, GCP project ID, etc.)
# Set initial_deploy = true for first apply

# 2. Apply infra (creates Artifact Registry, Cloud Run, secrets)
cd infra/envs/dev
terraform init
terraform apply

# 3. Build & push images, then deploy to Cloud Run
cd ../..
./scripts/build-and-push.sh dev

# 4. Set initial_deploy = false in terraform.tfvars and apply again
cd infra/envs/dev && terraform apply
```

## Subsequent Deploys

```bash
# Code changes only — build, push, and redeploy in one command
./scripts/build-and-push.sh dev   # or prod

# Infra config changes only
cd infra/envs/dev && terraform apply
```

## Custom Domains (Optional)

To map a custom domain (e.g. via Cloudflare) to Cloud Run:

1. Verify domain ownership in [Google Search Console](https://search.google.com/search-console)
2. Add to `terraform.tfvars`:
   ```hcl
   custom_domain_enabled  = true
   backend_custom_domain  = "api.example.com"
   frontend_custom_domain = "example.com"
   backend_url            = "https://api.example.com"
   frontend_url           = "https://example.com"
   ```
3. Run `terraform apply`
4. Add CNAME records in Cloudflare pointing to `ghs.googlehosted.com` (DNS only, grey cloud)

## Resources Created

| Resource | Description |
|---|---|
| Artifact Registry | Docker image registry (`anon-skill-dev` / `anon-skill-prod`) |
| Cloud Run: backend | FastAPI backend service |
| Cloud Run: frontend | Next.js frontend service |
| Secret Manager | `auth0-client-secret`, `gemini-api-key` |
| Service Account | Dedicated SA for backend with least-privilege access |

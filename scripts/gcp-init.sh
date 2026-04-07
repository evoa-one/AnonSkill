#!/bin/bash
# Run this once before `terraform apply` to enable required GCP APIs.
#
# Usage: ./scripts/gcp-init.sh [project-id]
set -e

PROJECT_ID=${1:-$(gcloud config get-value project)}

if [ -z "$PROJECT_ID" ]; then
  echo "Error: no project ID found. Run: gcloud config set project YOUR_PROJECT_ID"
  exit 1
fi

echo "Project: $PROJECT_ID"
echo ""

echo "Step 1: Logging in..."
gcloud auth login

echo ""
echo "Step 2: Setting up application default credentials..."
gcloud auth application-default login

echo ""
echo "Step 3: Setting default project..."
gcloud config set project "$PROJECT_ID"

echo ""
echo "Step 4: Enabling required GCP APIs..."
gcloud services enable \
  compute.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  --project="$PROJECT_ID"

echo ""
echo "Done! You can now run:"
echo "  cd infra/envs/dev  && terraform init && terraform apply"
echo "  cd infra/envs/prod && terraform init && terraform apply"

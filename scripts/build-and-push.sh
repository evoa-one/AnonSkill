#!/bin/bash
set -e

ENV=${1:-prod}  # Usage: ./scripts/build-and-push.sh [dev|prod]

PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"
REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/anon-skill-${ENV}"

echo "Environment : $ENV"
echo "Registry    : $REGISTRY"

# Configure Docker auth
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet

# Determine API URL based on env
if [ "$ENV" = "dev" ]; then
  API_URL="https://anon-skill-dev-backend-xxxx-uc.a.run.app"
  echo "NOTE: Update API_URL in this script after first terraform apply for dev."
else
  API_URL="https://api-anon-skill.evoa.one"
fi

# Backend
echo "Building backend..."
docker build --platform linux/amd64 -t ${REGISTRY}/backend:latest ./backend
docker push ${REGISTRY}/backend:latest

# Frontend
echo "Building frontend..."
docker build \
  --platform linux/amd64 \
  --build-arg NEXT_PUBLIC_API_URL=${API_URL} \
  -t ${REGISTRY}/frontend:latest \
  ./frontend
docker push ${REGISTRY}/frontend:latest

echo ""
echo "Done! Images pushed to $REGISTRY"
echo ""
echo "Next: cd infra/envs/${ENV} && terraform apply"

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

# Determine API URL — can be overridden via NEXT_PUBLIC_API_URL env var
# Usage: NEXT_PUBLIC_API_URL=https://my-api.example.com ./scripts/build-and-push.sh dev
if [ -n "$NEXT_PUBLIC_API_URL" ]; then
  API_URL="$NEXT_PUBLIC_API_URL"
elif [ "$ENV" = "dev" ]; then
  API_URL="https://api-anon-skill-dev.evoa.one"
else
  API_URL="https://api-anon-skill.evoa.one"
fi

echo "API URL     : $API_URL"

# Lint
echo "Running ruff..."
uv run ruff check ./backend
uv run ruff format --check ./backend

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

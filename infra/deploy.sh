#!/usr/bin/env bash
# Deploy the Granum API to Cloud Run.
#
# The API is a thin static server over the evolution artifacts (granum.web.api).
# This script curates the latest `runs/cell_payloads/*.json` into the tracked
# `api_data/` dir (which the Docker image bakes in), then deploys via Cloud Run
# source build (uses the root Dockerfile).
#
# The Next.js frontend deploys separately (Vercel recommended) with:
#   NEXT_PUBLIC_USE_REAL_API=true
#   NEXT_PUBLIC_API_BASE_URL=<the API URL printed below>
#
# Prereqs: gcloud auth + a project with billing + Cloud Run/Build APIs enabled.
#
# Usage:
#   GOOGLE_CLOUD_PROJECT=granum-2026 bash infra/deploy.sh
set -euo pipefail

PROJECT="${GOOGLE_CLOUD_PROJECT:?set GOOGLE_CLOUD_PROJECT}"
REGION="${GRANUM_REGION:-us-central1}"
SERVICE="${GRANUM_API_SERVICE:-granum-api}"

cd "$(dirname "$0")/.."

# 1. Curate the freshest evolution artifacts into the image data dir.
mkdir -p api_data
if compgen -G "runs/cell_payloads/*.json" > /dev/null; then
  cp -v runs/cell_payloads/*.json api_data/
else
  echo "WARN: no runs/cell_payloads/*.json found — deploying whatever is in api_data/" >&2
fi

if ! compgen -G "api_data/*.json" > /dev/null; then
  echo "ERROR: api_data/ is empty. Run 'granum evolve --reset' first." >&2
  exit 1
fi

# 2. Deploy (Cloud Run source build uses the root Dockerfile).
gcloud run deploy "$SERVICE" \
  --project "$PROJECT" \
  --region "$REGION" \
  --source . \
  --allow-unauthenticated \
  --port 8080 \
  --memory 256Mi \
  --cpu 1 \
  --max-instances 3

URL="$(gcloud run services describe "$SERVICE" --project "$PROJECT" --region "$REGION" --format='value(status.url)')"
echo ""
echo "=== Granum API deployed ==="
echo "  URL: $URL"
echo "  smoke: curl $URL/api/cells"
echo ""
echo "Point the frontend at it:"
echo "  NEXT_PUBLIC_USE_REAL_API=true NEXT_PUBLIC_API_BASE_URL=$URL"

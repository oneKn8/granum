#!/usr/bin/env bash
# Deploy the Granum API to Cloud Run.
#
# The API is a thin static server over the evolution artifacts (granum.web.api).
# It deploys the CURATED, committed `api_data/` artifacts (which the Docker image
# bakes in) via a Cloud Run source build (uses the root Dockerfile).
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

# 1. Deploy the CURATED, committed api_data/ artifacts — the demo source of truth.
#    We deliberately do NOT auto-copy raw runs/cell_payloads/ output: that would
#    un-curate the artifacts (re-add un-judged frontier nodes) and could clobber
#    the demo with whatever run happens to be on disk.
#
#    To refresh the demo from a fresh run, BAKE explicitly before deploying:
#      env -u PYTHONPATH uv run python scripts/bake_demo_artifact.py \
#        --src runs/cell_payloads/aetna_cardiac.json --dest api_data/aetna_cardiac.json
#    (then curate the coevolution artifact, review, and `git commit`), and re-run this.
if ! compgen -G "api_data/*.json" > /dev/null; then
  echo "ERROR: api_data/ has no artifacts. Bake one first (see comment above)." >&2
  exit 1
fi
echo "Deploying curated artifacts:"
for f in api_data/*.json; do echo "  - $f"; done

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

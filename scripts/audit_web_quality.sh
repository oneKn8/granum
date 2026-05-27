#!/usr/bin/env bash
# audit_web_quality.sh — pre-submission web-quality audit
#
# Invokes the web-quality-audit skill (Lighthouse + axe + Core Web Vitals)
# against either the live Cloud Run deploy or the local dev server.
#
# Usage:
#   scripts/audit_web_quality.sh                            # audits http://localhost:3001 (baseline)
#   scripts/audit_web_quality.sh https://granum-xxx.run.app # audits the deployed URL
#   AUDIT_URL=https://granum.app scripts/audit_web_quality.sh
#
# Outputs:
#   videos/audit/lighthouse_<timestamp>.json    raw lighthouse json
#   videos/audit/lighthouse_<timestamp>.html    human-readable report
#   videos/audit/axe_<timestamp>.json           axe-core a11y findings
#   videos/audit/SUMMARY.md                     one-line-per-metric digest
#
# 2026-pass bar (per .claude/rules/agents/tier2/website-designer.md step 9):
#   LCP < 2.0s
#   INP < 150ms
#   CLS < 0.05
#   WCAG 2.2 AA clean (axe-core)
#   JSON-LD LocalBusiness/MedicalOrganization schema present
#
# This script is the orchestrator; the skill itself runs inside Claude via mcp__chrome-devtools.
# When run directly from a shell (not from Claude), it falls back to local lighthouse-cli
# if installed, otherwise prints the skill invocation needed.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AUDIT_DIR="${REPO_ROOT}/videos/audit"
mkdir -p "${AUDIT_DIR}"

URL="${1:-${AUDIT_URL:-http://localhost:3001}}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LH_JSON="${AUDIT_DIR}/lighthouse_${TIMESTAMP}.json"
LH_HTML="${AUDIT_DIR}/lighthouse_${TIMESTAMP}.html"

echo "================================================================"
echo "Granum web-quality audit"
echo "================================================================"
echo "Target URL:  ${URL}"
echo "Timestamp:   ${TIMESTAMP}"
echo "Output dir:  ${AUDIT_DIR}"
echo

if [[ "${URL}" == http://localhost:* ]]; then
  if ! curl -sf -o /dev/null --max-time 3 "${URL}"; then
    echo "ERROR: ${URL} is not responding. Start the dev server first:"
    echo "    cd web && pnpm dev"
    exit 1
  fi
  echo "NOTE: auditing localhost dev build. For submission, re-run against the Cloud Run URL"
  echo "      so Lighthouse measures the production bundle + real CDN/edge latency."
  echo
fi

# Preferred path: invoke the web-quality-audit Claude skill (chrome-devtools MCP).
# When run inside Claude, the user does:
#   /web-quality-audit URL=${URL}
# That skill writes its own report; this script just ensures the audit dir exists.

# Fallback path: local lighthouse-cli (works in plain shell, no Claude needed).
if command -v lighthouse >/dev/null 2>&1; then
  echo "Running local lighthouse..."
  lighthouse "${URL}" \
    --output=json --output=html \
    --output-path="${AUDIT_DIR}/lighthouse_${TIMESTAMP}" \
    --chrome-flags="--headless --no-sandbox" \
    --quiet \
    --form-factor=desktop \
    --throttling-method=simulate \
    --only-categories=performance,accessibility,seo,best-practices

  echo
  echo "Wrote ${LH_JSON} + ${LH_HTML}"
  # Extract the four scores
  if command -v jq >/dev/null 2>&1; then
    echo
    echo "Category scores (0-100):"
    jq -r '.categories | to_entries[] | "  \(.key | ascii_upcase): \(.value.score * 100 | floor)"' "${LH_JSON}"
    echo
    echo "Core Web Vitals:"
    jq -r '.audits | "  LCP: \(."largest-contentful-paint".displayValue // "n/a")\n  CLS: \(."cumulative-layout-shift".displayValue // "n/a")\n  TBT: \(."total-blocking-time".displayValue // "n/a")"' "${LH_JSON}"
  fi
else
  echo "lighthouse-cli not found locally."
  echo
  echo "OPTION A — invoke the web-quality-audit skill from inside Claude:"
  echo "    /web-quality-audit URL=${URL}"
  echo
  echo "OPTION B — install lighthouse-cli and re-run this script:"
  echo "    npm install -g lighthouse"
  echo "    scripts/audit_web_quality.sh ${URL}"
  exit 0
fi

# Append a one-line summary to videos/audit/SUMMARY.md
SUMMARY="${AUDIT_DIR}/SUMMARY.md"
if [[ ! -f "${SUMMARY}" ]]; then
  echo "# Granum web-quality audit log" >"${SUMMARY}"
  echo >>"${SUMMARY}"
  echo "| Timestamp (UTC) | URL | Perf | A11y | Best | SEO |" >>"${SUMMARY}"
  echo "|---|---|---|---|---|---|" >>"${SUMMARY}"
fi

if command -v jq >/dev/null 2>&1; then
  PERF=$(jq -r '.categories.performance.score * 100 | floor' "${LH_JSON}")
  A11Y=$(jq -r '.categories.accessibility.score * 100 | floor' "${LH_JSON}")
  BEST=$(jq -r '.categories["best-practices"].score * 100 | floor' "${LH_JSON}")
  SEO=$(jq -r '.categories.seo.score * 100 | floor' "${LH_JSON}")
  echo "| ${TIMESTAMP} | ${URL} | ${PERF} | ${A11Y} | ${BEST} | ${SEO} |" >>"${SUMMARY}"
  echo
  echo "Appended summary line to ${SUMMARY}"
fi

echo
echo "Done. Open the HTML report:"
echo "    xdg-open ${LH_HTML} || open ${LH_HTML}"

#!/usr/bin/env bash
# Granum demo orchestrator.
#
# Drives a deterministic demo of the affinity-maturation loop end-to-end,
# starts the Next.js web app, and pauses on each beat so a screen recorder
# (or Playwright MCP capture) can grab frames. See docs/demo-script.md and
# docs/storyboard.md for the beat-by-beat plan.
#
# Env knobs:
#   DEMO_PACE       seconds between beats (default 8)
#   DEMO_FRESH      "1" to reset Phoenix state + db before running
#   DEMO_CELL       cell to drive (default aetna_cardiac)
#   DEMO_CYCLES     number of evolution cycles (default 8)
#   DEMO_SEED       deterministic seed (default 42)
#   DEMO_WEB_PORT   override port for the web dev server (default 3000)
#   DEMO_OPEN       "1" to xdg-open the cell page once the server is up
#
# Usage:
#   bash scripts/demo.sh
#   DEMO_FRESH=1 DEMO_PACE=12 bash scripts/demo.sh
#
# Boundaries (Terminal C scope):
#   This script ONLY calls existing `granum` CLI commands + the web server.
#   It does not write Python code. If `granum doctor` fails, surface the
#   error and stop — that's Terminal A's job to fix.

set -euo pipefail

# ---- knobs --------------------------------------------------------------

DEMO_PACE="${DEMO_PACE:-8}"
DEMO_FRESH="${DEMO_FRESH:-0}"
DEMO_CELL="${DEMO_CELL:-aetna_cardiac}"
DEMO_CYCLES="${DEMO_CYCLES:-8}"
DEMO_SEED="${DEMO_SEED:-42}"
DEMO_WEB_PORT="${DEMO_WEB_PORT:-3000}"
DEMO_OPEN="${DEMO_OPEN:-0}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_DIR="${REPO_ROOT}/web"

cd "${REPO_ROOT}"

# ---- helpers ------------------------------------------------------------

# IBM Plex serif for terminal output? Stick to plain text — log will be piped
# into the screen recorder's overlay track if the operator wants it.
beat() {
  local n="$1"; shift
  printf "\n\033[1m[beat %s]\033[0m %s\n" "$n" "$*"
}

run() {
  printf "  $ %s\n" "$*"
  "$@"
}

pause() {
  printf "  -- pause %ss --\n" "${DEMO_PACE}"
  sleep "${DEMO_PACE}"
}

cleanup() {
  if [[ -n "${WEB_PID:-}" ]] && kill -0 "${WEB_PID}" 2>/dev/null; then
    printf "\n[demo] stopping web server (pid %s)\n" "${WEB_PID}"
    kill "${WEB_PID}" 2>/dev/null || true
    wait "${WEB_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

# ---- preflight ----------------------------------------------------------

beat 0 "preflight"
if ! command -v uv >/dev/null 2>&1; then
  echo "uv not on PATH. install: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
  exit 1
fi
if ! command -v pnpm >/dev/null 2>&1; then
  echo "pnpm not on PATH (try: corepack enable && corepack prepare pnpm@latest --activate)" >&2
  exit 1
fi
run uv run granum --version
run uv run granum doctor

# ---- optional fresh state ----------------------------------------------

if [[ "${DEMO_FRESH}" == "1" ]]; then
  beat 0.5 "reset state (DEMO_FRESH=1)"
  run uv run granum reset --cell "${DEMO_CELL}" --yes
fi

# ---- seed -------------------------------------------------------------

beat 1 "seed gen-0 baseline"
run uv run granum seed --cell "${DEMO_CELL}" --seed "${DEMO_SEED}"
pause

# ---- evolution cycles --------------------------------------------------

for ((g=1; g<=DEMO_CYCLES; g++)); do
  beat "2.${g}" "cycle ${g}/${DEMO_CYCLES} — selection · tournament · apoptosis · mutation"
  run uv run granum cycle \
    --cell "${DEMO_CELL}" \
    --seed "$((DEMO_SEED + g))" \
    --judge-rationale
  pause
done

# ---- start web server --------------------------------------------------

beat 3 "start web server on port ${DEMO_WEB_PORT}"
pushd "${WEB_DIR}" >/dev/null
PORT="${DEMO_WEB_PORT}" pnpm dev >"${REPO_ROOT}/videos/web-dev.log" 2>&1 &
WEB_PID=$!
popd >/dev/null
printf "  web pid: %s\n" "${WEB_PID}"

# Wait for the server to bind (max 60s).
for _ in {1..60}; do
  if curl -fs -o /dev/null "http://localhost:${DEMO_WEB_PORT}"; then
    printf "  web ready: http://localhost:%s/cell/%s\n" "${DEMO_WEB_PORT}" "${DEMO_CELL}"
    break
  fi
  sleep 1
done
if ! curl -fs -o /dev/null "http://localhost:${DEMO_WEB_PORT}"; then
  echo "web server did not come up within 60s; see videos/web-dev.log" >&2
  exit 2
fi

# ---- open cell page ----------------------------------------------------

CELL_URL="http://localhost:${DEMO_WEB_PORT}/cell/${DEMO_CELL}"
if [[ "${DEMO_OPEN}" == "1" ]] && command -v xdg-open >/dev/null 2>&1; then
  beat 4 "open ${CELL_URL}"
  xdg-open "${CELL_URL}" >/dev/null 2>&1 || true
else
  beat 4 "ready to capture — open ${CELL_URL} in your browser or Playwright session"
fi

# ---- hold-open loop ----------------------------------------------------

printf "\n[demo] web server holding open. ctrl-c to stop.\n"
printf "[demo] capture frames per docs/storyboard.md while the server runs.\n"

# Keep the process alive so the screen recorder has time to grab frames.
# Operator can ctrl-c when done.
wait "${WEB_PID}"

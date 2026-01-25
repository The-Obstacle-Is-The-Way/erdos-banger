#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

WORKDIR="$(mktemp -d)"
cleanup() {
  rm -rf "${WORKDIR}"
}
trap cleanup EXIT

DATA_DIR="${WORKDIR}/data"
INDEX_DIR="${WORKDIR}/index"
LEAN_DIR="${WORKDIR}/formal/lean"

mkdir -p "${DATA_DIR}" "${INDEX_DIR}"
cp "${REPO_ROOT}/tests/fixtures/sample_problems.yaml" "${DATA_DIR}/problems_enriched.yaml"

export ERDOS_DATA_PATH="${DATA_DIR}"
export ERDOS_INDEX_PATH="${INDEX_DIR}/erdos.sqlite"

UV_RUN="uv run --frozen"

cd "${REPO_ROOT}"

echo "=== Erdos Smoke Test ==="

echo "[1/5] Loading problems..."
${UV_RUN} erdos list --limit 1 > /dev/null

echo "[2/5] Building search index..."
${UV_RUN} erdos search prime --build-index --limit 1 > /dev/null

echo "[3/5] Searching..."
${UV_RUN} erdos search prime --limit 1 > /dev/null

echo "[4/5] Generating Lean skeleton..."
${UV_RUN} erdos lean init --no-mathlib --path "${LEAN_DIR}" > /dev/null
${UV_RUN} erdos lean formalize 6 --path "${LEAN_DIR}" > /dev/null

echo "[5/5] Checking Lean (optional)..."
if command -v lean &> /dev/null && command -v lake &> /dev/null; then
  echo "      Lean found, checking minimal project..."
  ${UV_RUN} erdos lean check "${LEAN_DIR}/Erdos/Basic.lean" --path "${LEAN_DIR}" > /dev/null

  # `--no-mathlib` intentionally avoids fetching mathlib for a fast, offline smoke test.
  # Only run Problem006 compilation when mathlib is present in the project.
  if [[ -d "${LEAN_DIR}/.lake/packages/mathlib" || -d "${LEAN_DIR}/lake-packages/mathlib" ]]; then
    echo "      mathlib found, checking generated skeleton..."
    ${UV_RUN} erdos lean check "${LEAN_DIR}/Erdos/Problem006.lean" --path "${LEAN_DIR}" > /dev/null
  else
    echo "      mathlib not installed, skipping skeleton compilation"
  fi
else
  echo "      Lean not installed, skipping"
fi

echo ""
echo "✓ All systems operational"

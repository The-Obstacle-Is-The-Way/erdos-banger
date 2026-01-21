#!/usr/bin/env bash
# Ralph Wiggum Loop Runner
# Usage: ./scripts/ralph-loop.sh

set -euo pipefail

cd "$(dirname "$0")/.."

MAX="${MAX:-50}"
TIMEOUT="${TIMEOUT:-14400}"
ITER_TIMEOUT="${ITER_TIMEOUT:-600}"

# Find timeout command
TIMEOUT_CMD=""
if command -v gtimeout >/dev/null 2>&1; then
    TIMEOUT_CMD="gtimeout"
elif command -v timeout >/dev/null 2>&1; then
    TIMEOUT_CMD="timeout"
else
    echo "Missing timeout command. Install coreutils (macOS) or use Linux timeout." >&2
    exit 1
fi

echo "Ralph Wiggum Loop starting..."
echo "  Branch: $(git branch --show-current)"
echo "  Max iterations: $MAX"
echo "  Session timeout: ${TIMEOUT}s"
echo "  Iteration timeout: ${ITER_TIMEOUT}s"
echo ""

rm -rf logs/ralph 2>/dev/null || true
mkdir -p logs/ralph

for i in $(seq 1 "$MAX"); do
    n=$(printf "%03d" "$i")
    log="logs/ralph/iteration_${n}.log"

    echo "=== Iteration $i/$MAX ===" | tee -a "$log"

    # Run claude with iteration timeout
    "$TIMEOUT_CMD" "$ITER_TIMEOUT" claude --dangerously-skip-permissions -p "$(cat PROMPT.md)" 2>&1 | tee -a "$log" || true

    # Check if all tasks complete
    if ! grep -q "^\- \[ \]" PROGRESS.md; then
        echo "All tasks complete!" | tee -a "$log"
        break
    fi

    sleep 2
done

echo "Ralph loop finished."

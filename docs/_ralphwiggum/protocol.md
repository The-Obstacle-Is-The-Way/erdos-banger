# Ralph Wiggum Loop Protocol

**Created:** 2026-01-18
**Author:** Ray + Claude
**Status:** Ready for Use

---

## What is the Ralph Wiggum Technique?

The Ralph Wiggum technique (created by [Geoffrey Huntley](https://ghuntley.com/ralph/)) is an iterative AI development methodology where the **same prompt is run repeatedly** until objective completion criteria are met. The "self-referential" part is that each iteration sees its **previous work in files and git history**, not that model output is fed back as input.

**Core insight:** Fresh context each iteration. No garbage accumulation.

```bash
while :; do cat PROMPT.md | claude ; done
```

### Why It Works

- **Same prompt, repeated** = Iteration beats one-shot perfection
- **State tracked in files** = Progress persists across iterations
- **Atomic commits** = Easy to audit, revert, or cherry-pick
- **Sandboxed branch** = Safe experimentation
- **Fresh context** = No context pollution from failed attempts

### Key Quote

> "Deterministically bad in an undeterministic world" - failures are predictable, enabling systematic improvement through prompt tuning.

---

## Prerequisites

### Tools Required

```bash
# Claude Code CLI
npm install -g @anthropic-ai/claude-code

# tmux (for persistent sessions)
brew install tmux  # macOS
apt install tmux   # Linux

# uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Project Requirements

1. **State file** (`PROGRESS.md`) - Tracks what's done/pending
2. **Prompt file** (`PROMPT.md`) - Instructions for each iteration
3. **Debt/Bug docs** (`docs/debt/`, `docs/bugs/`) - SSOT for sprint work
   - Specs (`docs/specs/`) only when approved for new feature work
4. **Git repo** - For atomic commits and history

---

## Setup Protocol

### Step 1: Create Branch Structure

**CRITICAL:** Always sandbox Ralph work in a dedicated branch.

```bash
# Start from dev
git checkout dev
git pull --ff-only origin dev  # Human pre-flight on dev (not on the Ralph branch)

# Create Ralph branch
git checkout -b ralph-wiggum-<sprint>

# Push to remote for backup
git push -u origin ralph-wiggum-<sprint>
```

**Branch hierarchy:**
```
main (protected, production)
  └── dev (integration, manual merges)
        └── ralph-wiggum-<sprint> (autonomous work)
```

### Step 2: File Structure

```
erdos-banger/
├── PROMPT.md                    # Loop prompt (root)
├── PROGRESS.md                  # State tracker (root)
├── logs/ralph/                  # Per-iteration logs (gitignored; safe to delete between runs)
├── docs/
│   ├── _ralphwiggum/
│   │   └── protocol.md          # This file
│   ├── debt/                    # Active debt decks (SSOT for debt sprints)
│   ├── bugs/                    # Active bug decks (SSOT for bug sprints)
│   ├── specs/                   # Active specs (v1.2+)
│   └── _archive/specs/          # Archived specs (implemented SSOT)
```

### Step 3: Start tmux Session

```bash
# Create named session
tmux new-session -s erdos-ralph

# Or attach to existing
tmux attach -t erdos-ralph

# Detach without killing: Ctrl+B, then D
# Kill session: tmux kill-session -t erdos-ralph
```

### Step 4: Run the Loop

```bash
# Navigate to project
cd /path/to/erdos-banger
git checkout ralph-wiggum-<sprint>

# THE RALPH LOOP (bounded by iteration + wall-clock timeouts)
#
# Linux: `timeout` is typically available.
# macOS: install coreutils and use `gtimeout`:
#   brew install coreutils
#
# Optional: set TIMEOUT_CMD explicitly:
#   TIMEOUT_CMD=gtimeout

MAX=50
TIMEOUT=14400      # 4 hours total max
ITER_TIMEOUT=600   # 10 minutes per iteration max

TIMEOUT_CMD="${TIMEOUT_CMD:-}"
if [[ -z "$TIMEOUT_CMD" ]]; then
  if command -v timeout >/dev/null 2>&1; then
    TIMEOUT_CMD="timeout"
  elif command -v gtimeout >/dev/null 2>&1; then
    TIMEOUT_CMD="gtimeout"
  else
    echo "Missing timeout command. Install coreutils (macOS) or use Linux `timeout`." >&2
    exit 1
  fi
fi

rm -rf logs/ralph 2>/dev/null || true
mkdir -p logs/ralph

"$TIMEOUT_CMD" "$TIMEOUT" bash -c '
  for i in $(seq 1 '"$MAX"'); do
    n=$(printf "%03d" "$i")
    log="logs/ralph/iteration_${n}.log"
    echo "=== Iteration $i/'"$MAX"' ===" | tee -a "$log"
    '"$TIMEOUT_CMD"' '"$ITER_TIMEOUT"' claude --dangerously-skip-permissions -p "$(cat PROMPT.md)" 2>&1 | tee -a "$log"
    # Check if all tasks complete (no unchecked boxes)
    if ! grep -q "^\- \[ \]" PROGRESS.md; then
      echo "All tasks complete!" | tee -a "$log"
      break
    fi
    sleep 2
  done
'
```

---

## erdos-banger Specific Configuration

### Quality Gates (MUST PASS)

```bash
uv run pre-commit run --all-files  # All hooks
uv run ruff check .                # Lint
uv run ruff format --check .       # Format check
uv run mypy src/ tests/            # Type check
uv run pytest -m "not requires_lean and not requires_network" --cov=erdos --cov-fail-under=80
```

Or use the Makefile:

```bash
make ci  # Runs format-check, lint, typecheck, cov
```

### Test Markers

- `requires_lean` - Skip if Lean not installed
- `requires_network` - Skip for offline tests
- Default: `-m "not requires_lean and not requires_network"`

### Atomic Commit Format

```bash
git add -A && git commit -m "$(cat <<'EOF'
[SPEC-010] Implement: arXiv metadata client

- Added src/erdos/core/arxiv_client.py
- Unit tests in tests/unit/test_arxiv_client.py
- Quality gates passed
EOF
)"
```

---

## Overnight Safety Guardrails (Non-negotiable)

### File Modification Boundaries

Allowed to change:
- `src/erdos/**`
- `tests/**`
- `docs/specs/**` (active specs only)
- `docs/bugs/**`, `docs/debt/**`
- `PROMPT.md`, `PROGRESS.md`, `docs/_ralphwiggum/**`

Forbidden to change (treat as immutable SSOT unless a human explicitly authorizes it):
- `docs/_archive/**`
- `data/erdosproblems/**` (git submodule)

Dependency manifests:
- `pyproject.toml` and `uv.lock` may be edited **only when a spec explicitly requires it** (e.g., when a spec's "Dependencies" section lists a new runtime dependency), and must be followed by `uv lock --check` and `uv sync --frozen`.

### Resource Limits

- Max files changed per iteration: **10**
- Max net-new lines per iteration: **~500**
- Max iterations per overnight run: **50** (hard stop)
- Max wall-clock runtime per run: **4 hours** (recommended)
- Max wall-clock runtime per iteration: **10 minutes** (recommended)
- Max “stuck” retries on the same failing gate: **3**

### Cost / Budget Awareness (Recommended)

- Treat long runs as potentially expensive (LLM usage + CI cycles). Use `MAX`, `TIMEOUT`, and `ITER_TIMEOUT` as your primary budget caps.
- Monitor output under `logs/ralph/` and watch `git log --oneline -10` to confirm forward progress.
- If you see repeated failures or no commits for multiple iterations, abort and investigate rather than letting the loop burn time/budget.

### No-Reward-Hack Rules

- Never delete/disable tests to make CI green.
- Never "mock the unit under test"; mock only boundaries (network/subprocess/time).
- Never lower coverage thresholds, relax lint rules, or bypass mypy strictness.
- **Never write documentation ABOUT work as a substitute for DOING work.** If a task is too big, break it into subtasks in PROGRESS.md AND start the first subtask in the same iteration. Escalation documents (debt docs) are only valid if you've genuinely hit a blocker (missing deps, spec contradiction, repeated gate failures) - not because "it's big."
- **"Too big" is not a blocker.** Break it down and keep working. The only valid blockers are: missing dependencies, spec contradictions, and quality gate failures after 3 attempts.

### Push Strategy (Remote Backup)

After each atomic commit:

```bash
git push
```

**If push fails with "branches have diverged":**

```bash
git push --force-with-lease
```

This is safe because the Ralph branch is autonomous - you are the only committer. **On the Ralph branch during autonomous execution, NEVER use `git rebase` or `git pull`** - these cause merge conflicts that derail the loop.

If pushing is blocked (auth/CI outage), stop the loop and request human intervention.

---

## TDD Enforcement (Ironclad)

### The TDD Cycle

1. **RED**: Write a failing test first
2. **GREEN**: Write minimal code to pass
3. **REFACTOR**: Clean up, keep tests green

### TDD Rules (Non-negotiable)

1. **No production code without a failing test first**
2. **One test at a time** - Don't batch tests
3. **Minimal implementation** - Only enough to pass the current test
4. **Refactor only when green** - Never refactor with failing tests
5. **Tests document behavior** - Tests are the specification

### Spec → Test → Code Flow

```
docs/debt/debt-XXX-*.md                # Read the debt deck (or a spec doc)
    ↓
tests/unit/test_arxiv_client.py        # Write failing test
    ↓
src/erdos/core/arxiv_client.py         # Implement to pass
    ↓
make ci                                 # Verify all gates pass
    ↓
git commit                              # Atomic commit
```

---

## Critical Review Prompt

Before changing code/docs based on feedback (human reviews, CodeRabbit, another model, your own prior output), apply this block and validate claims against SSOT:

```text
Review the claim or feedback (it may be from an internal or external agent).
Validate every claim from first principles. If—and only if—it's true and
helpful, update the system to align with the SSOT, implemented cleanly and
completely (Rob C. Martin discipline). Find and fix all half-measures,
reward hacks, and partial fixes if they exist. Be critically adversarial
with good intentions for constructive criticism. Ship the exact end-to-end
implementation we need.
```

---

## SPEC-* Self-Review Protocol

**Before picking up a new task**, check if the MOST RECENTLY completed item is a `SPEC-*` WITHOUT a `[REVIEWED]` marker.

If yes, **THIS ITERATION IS A REVIEW ITERATION**:

1. Read the spec doc and its acceptance criteria
2. Verify the implementation matches ALL acceptance criteria
3. Apply the Critical Review Prompt to your own prior work
4. Check for half-measures:
   - Are there TODO comments that should be resolved?
   - Do tests cover all acceptance criteria?
   - Does SSOT (code) match the spec?
5. **If issues found**:
   - Create a fixup task in PROGRESS.md
   - Mark the original as `[NEEDS-FIX]` instead of `[REVIEWED]`
   - Commit and exit
6. **If verified clean**:
   - Add `[REVIEWED]` marker to the spec line
   - Commit and exit (do NOT start next task this iteration)

---

## Stop Conditions

The loop stops when:

1. **All tasks complete** - No unchecked `[ ]` in PROGRESS.md
2. **Iteration limit reached** - MAX=50 by default
3. **Manual intervention** - Ctrl+C
4. **Escalation trigger** - A stop condition from PROMPT.md is hit (ambiguous spec, missing deps, repeated gate failures, etc.)

**IMPORTANT: State-based verification prevents reward hacking.**

```bash
# Good: Check actual state
if ! grep -q "^\- \[ \]" PROGRESS.md; then
  echo "All tasks complete"
  break
fi

# Bad: Parse model output for magic phrases (don't do this)
# if output contains "PROJECT COMPLETE"; then break
```

---

## Monitoring

### Watch Progress

```bash
# In another terminal/tmux pane
watch -n 5 'head -50 PROGRESS.md'

# Or check git activity
watch -n 5 'git log --oneline -10'
```

### Check Loop Status

```bash
# See recent commits
git log --oneline -20

# See what changed
git diff HEAD~1

# Quick verification
make smoke
```

---

## Post-Loop Audit

### Review All Changes

```bash
# See all commits from Ralph
git log dev..ralph-wiggum-<sprint> --oneline

# See full diff
git diff dev..ralph-wiggum-<sprint> --stat

# Review specific commit
git show <commit-hash>
```

### Final Verification

```bash
# All quality gates
make ci

# Smoke test
make smoke

# Full test suite (if Lean available)
make test-all
```

### Merge if Good

```bash
# Option 1: Direct merge
git checkout dev
git merge ralph-wiggum-<sprint>

# Option 2: PR for review
gh pr create --base dev --head ralph-wiggum-<sprint> \
  --title "Ralph Wiggum v1.1: Implement specs 010-017" \
  --body "Automated implementation via Ralph Wiggum loop"
```

### Revert if Bad

```bash
# Nuclear option - delete branch entirely
git checkout dev
git branch -D ralph-wiggum-<sprint>

# Or revert specific commits
git revert <bad-commit-hash>
```

---

## Best Practices

### Research Notes (2025–2026)

These sources inform the guardrails and the “why” behind the protocol:

- Ralph Wiggum technique: repeated identical prompts, state in files, deterministic iteration loop. https://ghuntley.com/ralph/
- Field report: running agents in loops overnight; emphasizes frequent commits/pushes and keeping scope bounded. https://github.com/repomirrorhq/repomirror/blob/main/repomirror.md
- Aider edit formats: search/replace (“diff”) blocks reduce brittle line-number failures compared to unified diffs. https://aider.chat/docs/more/edit-formats.html
- Aider benchmarks: deterministic harnesses; validate success by passing real unit tests; limit the amount of error output fed back to reduce noise. https://aider.chat/docs/benchmarks.html
- SWE-agent: interface design (agent-computer interface) strongly impacts autonomous SE performance; a structured ACI improves navigation/edit/test execution. https://arxiv.org/abs/2405.15793
- Context “rot”: long contexts degrade reliability; keep prompts small and use byte/line caps. https://research.trychroma.com/context-rot
- Reward hacking: feedback loops need explicit constraints and invariants to prevent gaming metrics. https://arxiv.org/html/2402.06627v3

### DO

- Always sandbox in dedicated branch
- Use detailed specs for each task
- Require atomic commits
- Set clear completion criteria
- Set iteration limits
- Monitor periodically
- Audit before merging
- Follow TDD strictly
- Keep prompts and error logs small (avoid context rot): prefer summaries and capped error output
- Prefer “state-based” completion checks (PROGRESS.md), not “model said done”
- Push after each commit (remote backup)

### DON'T

- Run on main/dev branch directly
- Skip the state file
- Allow multi-task iterations
- Trust without auditing
- Use vague task descriptions
- Run without iteration limits
- Skip the review iteration for SPEC-* tasks
- Let the agent mutate `docs/_archive/` or `data/erdosproblems/` as “fixes”
- Let the agent change quality gates or coverage thresholds to make CI green

---

## Troubleshooting

### Loop Stops Unexpectedly

```bash
# Check if Claude is running
ps aux | grep claude

# Check tmux session
tmux list-sessions

# Restart loop in tmux
tmux attach -t erdos-ralph
```

### Quality Gates Failing

- Loop should auto-fix on next iteration
- If persistent, check the spec for clarity
- May need manual intervention

### Context Drift

Fresh context each iteration prevents this. If issues arise:
1. Check PROGRESS.md is being read first
2. Ensure specs are clear and complete
3. Reset to last known good commit if needed

---

## References

- [Geoffrey Huntley - Ralph Wiggum](https://ghuntley.com/ralph/)
- [how-to-ralph-wiggum repo](https://github.com/ghuntley/how-to-ralph-wiggum)
- [Dev Interrupted interview](https://devinterrupted.substack.com/p/inventing-the-ralph-wiggum-loop-creator)

---

## Quick Start Checklist

For a step-by-step pre-flight, see `docs/_ralphwiggum/LAUNCH_CHECKLIST.md`.

```bash
# 1. Create sandbox branch
git checkout dev && git pull --ff-only origin dev
git checkout -b ralph-wiggum-<sprint>

# 2. Ensure PROGRESS.md and PROMPT.md exist in root
ls PROGRESS.md PROMPT.md

# 3. Ensure spec docs exist
# Debt sprint:
ls docs/debt/README.md docs/debt/debt-0*.md
#
# Spec work (when approved):
ls docs/specs/spec-0*.md docs/_archive/specs/spec-0*.md

# 4. Start tmux
tmux new -s erdos-ralph

# 5. Run the loop (bounded by timeouts; logs captured)
MAX=50
TIMEOUT=14400
ITER_TIMEOUT=600

TIMEOUT_CMD="${TIMEOUT_CMD:-}"
if [[ -z "$TIMEOUT_CMD" ]]; then
  if command -v timeout >/dev/null 2>&1; then
    TIMEOUT_CMD="timeout"
  elif command -v gtimeout >/dev/null 2>&1; then
    TIMEOUT_CMD="gtimeout"
  else
    echo "Missing timeout command. Install coreutils (macOS) or use Linux `timeout`." >&2
    exit 1
  fi
fi

rm -rf logs/ralph 2>/dev/null || true
mkdir -p logs/ralph

"$TIMEOUT_CMD" "$TIMEOUT" bash -c '
  for i in $(seq 1 '"$MAX"'); do
    n=$(printf "%03d" "$i")
    log="logs/ralph/iteration_${n}.log"
    echo "=== Iteration $i/'"$MAX"' ===" | tee -a "$log"
    '"$TIMEOUT_CMD"' '"$ITER_TIMEOUT"' claude --dangerously-skip-permissions -p "$(cat PROMPT.md)" 2>&1 | tee -a "$log"
    if ! grep -q "^\- \[ \]" PROGRESS.md; then
      echo "All tasks complete" | tee -a "$log"
      break
    fi
    sleep 2
  done
'

# 6. Monitor in another pane (optional)
watch -n 5 'git log --oneline -10'

# 7. Audit when done
git log dev..ralph-wiggum-<sprint> --oneline
git diff dev..ralph-wiggum-<sprint> --stat
make ci

# 8. Merge if good
git checkout dev && git merge ralph-wiggum-<sprint>
```

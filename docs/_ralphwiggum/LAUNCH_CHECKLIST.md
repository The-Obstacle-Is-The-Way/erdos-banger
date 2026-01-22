# Ralph Wiggum Launch Checklist (Pre-Flight)

Use this checklist before starting an overnight autonomous run.

---

## 0) One-Time Machine Setup

- [ ] `git` installed and configured
- [ ] `gh` installed and authenticated (`gh auth status`)
- [ ] `uv` installed (`uv --version`)
- [ ] Claude Code CLI installed (`claude --version`)
- [ ] `tmux` installed (recommended for overnight runs)
- [ ] Timeout command available (Linux: `timeout`; macOS: `brew install coreutils` for `gtimeout`)

---

## 1) Repo Pre-Flight (Required Every Run)

From repo root:

```bash
pwd
git status
git branch --show-current
```

- [ ] Working tree is clean (no uncommitted changes)
- [ ] You will run the loop on a `ralph-wiggum-*` branch (not on `main`/`dev`)
- [ ] `PROMPT.md` and `PROGRESS.md` exist
- [ ] SSOT docs exist for the run:
  - Debt sprint: `docs/debt/README.md` and the referenced `docs/debt/debt-*.md` decks
  - Spec work (when approved): `docs/specs/` (active) and/or `docs/_archive/specs/` (implemented SSOT)

Sync and sanity:

```bash
git fetch origin
# Recommended: start a fresh Ralph branch from latest dev (avoid rebasing)
git checkout dev
git pull --ff-only origin dev
git checkout -b ralph-wiggum-<sprint>
git push -u origin ralph-wiggum-<sprint>
make sync-frozen
make lock-check
make ci
make smoke
make test-all  # Full suite (includes requires_network; may hit real APIs)
```

- [ ] `make ci` passes
- [ ] `make smoke` passes
- [ ] `make test-all` passes (recommended before/after a long sprint; may require network)

---

## 2) Safety Checks

- [ ] You understand the file boundaries in `docs/_ralphwiggum/protocol.md` (“Forbidden to change”)
- [ ] You are comfortable with the iteration cap (`MAX=50`)
- [ ] You have disk space (Lean + caches can grow)

---

## 3) Recommended Launch Command

Start a tmux session:

```bash
tmux new-session -s erdos-ralph
```

Run the loop:

```bash
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

mkdir -p logs/ralph

"$TIMEOUT_CMD" "$TIMEOUT" bash -c '
  for i in $(seq 1 '"$MAX"'); do
    n=$(printf "%03d" "$i")
    log="logs/ralph/iteration_${n}.log"
    echo "=== Iteration $i/'"$MAX"' ===" | tee -a "$log"
    '"$TIMEOUT_CMD"' '"$ITER_TIMEOUT"' claude --dangerously-skip-permissions -p "$(cat PROMPT.md)" 2>&1 | tee -a "$log"
    if ! grep -q "^\\- \\[ \\]" PROGRESS.md; then
      echo "All tasks complete" | tee -a "$log"
      break
    fi
    sleep 2
  done
'
```

---

## 4) Monitoring Instructions

In another pane:

```bash
watch -n 10 'git log --oneline -10'
watch -n 10 'head -80 PROGRESS.md'
```

If the loop appears stuck:

```bash
make ci
git status
```

---

## 5) Abort Instructions

- Stop the loop: Ctrl+C (inside the tmux pane running it)
- If needed, kill tmux session: `tmux kill-session -t erdos-ralph`

Rollback options:

```bash
git status
git log --oneline -10

# Undo last commit (discard changes)
git reset --hard HEAD~1

# Revert a specific commit (safe on shared branches)
git revert <sha>
```

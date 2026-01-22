# Ralph Wiggum Guardrails (Persistent Notes)

This document is a **living record** of guardrails, failure patterns, and “gotchas” observed while running long autonomous loops in this repo.

**Goal:** prevent repeated mistakes across sessions by making lessons durable.

---

## How to Use

- When a failure pattern is observed (reward hacking attempt, repeated CI failure, spec ambiguity), add an entry under **Observed Failure Patterns**.
- When we change the protocol/prompt/quality gates to address a pattern, record it under **Guardrail Changes** with the commit hash.
- Keep entries concrete and actionable (symptom → root cause → mitigation).

---

## Observed Failure Patterns

### FP-001: “Passes locally, fails in CI” drift

- Symptom: developer runs a subset of checks; CI fails on a different gate.
- Common cause: local workflow doesn’t run `make ci` (or pre-commit) before pushing.
- Mitigation: treat `make ci` as the minimum bar before every commit; keep CI and Makefile aligned.

### FP-002: Hung iteration (no progress, no output)

- Symptom: the loop stalls on an iteration (e.g., tool invocation never returns).
- Mitigation: enforce per-iteration timeouts and capture logs under `logs/ralph/` for post-mortem.

### FP-003: SSOT path drift (specs moved, checklists stale)

- Symptom: protocol/checklist references files that no longer exist (e.g., `docs/specs/spec-010-*.md` after specs are archived).
- Common cause: reorganizing docs without updating `docs/_ralphwiggum/**`.
- Mitigation: treat `docs/_ralphwiggum/**` as “operational SSOT” and update it in the same PR whenever docs move.

### FP-005: Git rebase derailment on push failure

- Symptom: Ralph hits "branches have diverged" and attempts `git rebase` or `git pull --rebase`, causing merge conflicts that stall the loop.
- Common cause: Multiple commits pushed in quick succession, or a race condition with the remote.
- Mitigation: **On the Ralph branch, NEVER use `git rebase` or `git pull`**. If `git push` fails due to divergence, use `git push --force-with-lease` (safe force push). The Ralph branch is autonomous - divergence means something unexpected happened, and force-push is the correct recovery.

### FP-004: Secrets accidentally end up in tracked logs

- Symptom: API keys (or other secrets) are copied into tracked files during debugging or loop summaries.
- Common cause: pasting raw `.env` content or command output into tracked files (docs, specs, prompts).
- Mitigation: never paste secrets; keep `.env` gitignored; scan tracked files and staged diffs before pushing:
  - `git diff --cached | rg -in "(sk-|sk-ant-|ghp_|AIza|arstl_|xoxb-|hf_)"` (what you're about to push)
  - `git ls-files -z | xargs -0 rg -in "(sk-|sk-ant-|ghp_|AIza|arstl_|xoxb-|hf_)"` (full tracked tree)

---

## Guardrail Changes (Protocol/Prompt/CI)

- 2026-01-21: Added FP-005 (git rebase derailment). Updated PROMPT.md and protocol.md to explicitly forbid `git rebase` and `git pull`, with `--force-with-lease` as the recovery for divergence.
- 2026-01-19: Added iteration + total runtime timeouts and per-iteration logs (`logs/ralph/`) to the recommended loop commands.

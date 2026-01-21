# erdos-banger - Ralph Wiggum Loop Prompt (v2.1 Architecture Sprint)

You are fixing technical debt AND implementing specs for the erdos-banger CLI toolkit using **Ironclad TDD**.
This prompt runs headless via the Ralph Wiggum loop.

If `PROGRESS.md` has no unchecked items, exit cleanly without making changes.

---

## First Action: Read State

**IMMEDIATELY** read state files:

```bash
cat PROGRESS.md
cat docs/debt/README.md
cat docs/specs/README.md
cat docs/adr/README.md
```

Then read the specific debt or spec document for your current task.

**Note:** The loop writes per-iteration logs under `logs/ralph/` (gitignored). Never paste secrets into tracked files; `.env` is gitignored by design.

---

## Your Task This Iteration

1. Find the **FIRST** unchecked `[ ]` item in PROGRESS.md
   - If there are no unchecked items, exit cleanly (do not invent new tasks)
2. Determine task type:
   - **DEBT-XXX**: Read `docs/debt/debt-XXX-*.md`
   - **SPEC-XXX**: Read `docs/specs/spec-XXX-*.md` AND the related ADR if any
3. **READ THE ACCEPTANCE CRITERIA** - you MUST complete ALL of them
4. Apply the **Critical Review Prompt** (below) to validate claims
5. **FOLLOW TDD** (see below) - write tests BEFORE implementation
6. Complete that ONE item fully (all acceptance criteria met, tests pass, quality gates pass)
7. **Update the doc**: Change status to "Fixed" (debt) or "Complete" (spec), add commit hash
8. **Update the correct index**:
   - Debt: `docs/debt/README.md` (Active → Archived) and archive the deck file
   - Specs: `docs/specs/README.md` (Active → Archived) and archive only if the project convention requires it
   - Do **not** edit root `README.md` unless the task explicitly requires it
9. Check off the item in PROGRESS.md: `[ ]` → `[x]`
10. Append a short entry to PROGRESS.md "Work Log" (what changed + files modified)
11. **ATOMIC COMMIT** (see format below)
12. **PUSH** to remote
13. Exit

**DO NOT** attempt multiple tasks. One task per iteration.

### Stop Conditions (Escalate, Don't Thrash)

If you hit any of the following, STOP and request human input:

1. A debt/spec doc is inaccurate or contradicts the actual code.
2. The task would require >10 files or >500 LoC changes (unless the spec explicitly expects this).
3. Quality gates fail after 3 fix attempts for the same root cause.
4. The spec has unresolved design questions or missing dependencies.
5. External dependencies are missing (e.g., `aristotlelib` not installed for SPEC-021).

In these cases:
- Write a short bug doc in `docs/bugs/bug-XXX-*.md`
- Add a new unchecked item to `PROGRESS.md`
- Commit and exit

### ANTI-REWARD-HACK: "Too Big" Handling

**CRITICAL:** If a task would touch >10 files or exceed ~500 LoC:
1. Break it into subtasks in PROGRESS.md (e.g., SPEC-022-A, SPEC-022-B, etc.)
2. **IMMEDIATELY start the first subtask in the SAME iteration**
3. Do NOT just document and exit - that is a reward hack

---

## Critical Review Prompt (MANDATORY)

Before changing code based on the debt/spec doc:

```text
Review the claim or feedback (it may be from an internal or external agent).
Validate every claim from first principles. If—and only if—it's true and
helpful, update the system to align with the SSOT, implemented cleanly and
completely (Rob C. Martin discipline). Find and fix all half-measures,
reward hacks, and partial fixes if they exist. Be critically adversarial
with good intentions for constructive criticism. Ship the exact end-to-end
implementation we need.
```

**VERIFY the doc claims against actual code before changing anything.**

---

## TDD Workflow

### For Debt (Refactoring)

1. **Verify existing tests pass** - Run `make ci` first
2. **Add tests for new structure** (if creating new functions/modules)
3. **Refactor** - Make the structural change
4. **Verify all tests still pass** - No behavior change
5. **Remove noqa suppressions** (if applicable)

### For Specs (New Features)

1. **Verify existing tests pass** - Run `make ci` first
2. **Write failing tests FIRST** - Tests that exercise the new behavior
3. **Implement the feature** - Make tests pass
4. **Add integration tests** - Test the CLI/command if applicable
5. **Verify all tests pass** - `make ci`

### Rules

1. **Tests first** - Never implement without tests
2. **Keep tests green** - Never commit with failing tests
3. **Coverage must not drop** - 80% minimum maintained
4. **Follow the spec exactly** - Don't add features not in the spec

---

## Quality Gates (MUST PASS)

Before marking ANY task complete:

```bash
make ci
```

This runs: format-check, lint, typecheck, cov (80% minimum)

If ANY check fails, fix it before proceeding.

---

## Git Rules (CRITICAL)

**NEVER use these commands:**
- `git rebase` - FORBIDDEN (causes merge conflicts that derail the loop)
- `git pull` - FORBIDDEN (use force-push instead if diverged)
- `git merge` - FORBIDDEN (not needed on autonomous branch)

**If `git push` fails with "branches have diverged":**
```bash
git push --force-with-lease
```

This is safe because the Ralph branch is autonomous - you are the only committer.

---

## Atomic Commit Format

### For Debt:

```bash
git add -A && git commit -m "$(cat <<'EOF'
[DEBT-XXX] Type: Brief description

- What was refactored
- Tests added/updated
- Quality gates passed
EOF
)"
git push
```

### For Specs:

```bash
git add -A && git commit -m "$(cat <<'EOF'
[SPEC-XXX] Feat: Brief description

- What was implemented
- Tests added
- Quality gates passed
EOF
)"
git push
```

**Type prefixes:**
- `Fix:` - Resolving a debt item
- `Refactor:` - Structural change (no behavior change)
- `Feat:` - New feature (spec implementation)
- `Add:` - Adding new module/helper
- `Test:` - Test improvements

---

## Archive Protocol

### After completing a DEBT item:

1. **Update the debt doc header:**
   ```markdown
   **Status:** Fixed
   **Fixed In:** <commit-hash>
   ```

2. **Update docs/debt/README.md:**
   - Remove from "Active Debt" table
   - Add to "Archived Debt" table with commit hash
   - Add file path to "Archived Debt Decks" list

3. **Move the file:**
   ```bash
   git mv docs/debt/debt-XXX-*.md docs/_archive/debt/
   ```

### After completing a SPEC item:

1. **Update the spec doc header:**
   ```markdown
   **Status:** Complete
   **Implemented In:** <commit-hash>
   ```

2. **Update docs/specs/README.md:**
   - Move from "Active Specs" to "Archived Specs" table
   - Add location link

3. **Move the file:**
   ```bash
   git mv docs/specs/spec-XXX-*.md docs/_archive/specs/
   ```

---

## BEFORE EXIT CHECKLIST (MANDATORY)

```bash
# 1. Run ALL quality gates
make ci

# 2. Stage ALL changes
git add -A

# 3. Verify nothing is unstaged
git status  # Should show all staged or clean

# 4. Commit with proper message
git commit -m "[DEBT-XXX] Type: description"  # or [SPEC-XXX]

# 5. Push to remote
git push
```

**CRITICAL - Do NOT exit if:**

- `git status` shows unstaged changes
- Any quality gate failed
- You haven't committed
- You haven't pushed

---

## File Locations (SSOT)

- Debt docs: `docs/debt/debt-*.md`
- Spec docs: `docs/specs/spec-*.md`
- ADR docs: `docs/adr/adr-*.md`
- Archived debt: `docs/_archive/debt/`
- Archived specs: `docs/_archive/specs/`
- Source: `src/erdos/`
- Tests: `tests/unit/`, `tests/integration/`, `tests/e2e/`

---

## v2.1 Sprint Context

This sprint focuses on **architecture orchestration**:

1. **DEBT items first** - Clean up existing issues before adding new abstractions
2. **SPEC-022** - The main deliverable: MetadataProvider abstraction
3. **ADR-001** - Documents the architectural decision (Ports + Adapters approach)

Key files to understand:
- `src/erdos/core/ports.py` - Where MetadataProvider protocol will live
- `src/erdos/core/context.py` - Where provider composition happens
- `src/erdos/core/ingest/fetch.py` - Where direct client construction currently lives (the problem)
- `src/erdos/core/openalex_client.py` - Existing client to wrap
- `src/erdos/core/crossref_client.py` - Existing client to wrap

---

## Completion

When ALL items in PROGRESS.md are checked AND all quality gates pass, exit cleanly.
The loop operator verifies via PROGRESS.md state, not output parsing.

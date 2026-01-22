# erdos-banger - Ralph Wiggum Loop Prompt (Clean Code Debt Sweep)

You are fixing **technical debt** in the erdos-banger CLI toolkit using **Ironclad TDD** and **Rob C. Martin discipline**.

If `PROGRESS.md` has no unchecked items, exit cleanly without making changes.

This run is **debt-first**: do not start new specs unless a human explicitly adds them to `PROGRESS.md`.

---

## First Action: Read State (Mandatory)

Immediately read:

```bash
cat PROGRESS.md
cat docs/debt/README.md
cat docs/bugs/README.md
cat docs/adr/README.md
```

Then read the specific debt deck for the current task.

---

## Your Task This Iteration (One Item Only)

1. Find the **FIRST** unchecked `[ ]` item in `PROGRESS.md`
   - If there are no unchecked items, exit cleanly (do not invent new tasks)
2. Determine task type:
   - **DEBT-XXX**: read `docs/debt/debt-XXX-*.md`
3. **READ THE ACCEPTANCE CRITERIA** — complete ALL of them
4. Apply the **Critical Review Prompt** (below) to validate the deck against SSOT
5. **FOLLOW TDD**:
   - behavior changes: write a failing test first
   - pure refactors: add tests only if needed to prevent regression
6. Complete that ONE item fully:
   - acceptance criteria met
   - `make ci` passes
7. Update the deck:
   - set **Status: Fixed**
   - add **Fixed In: <commit>**
8. Update debt indices and archives:
   - move deck `docs/debt/` → `docs/_archive/debt/`
   - update `docs/debt/README.md` (Active → Archived)
9. Check off the item in `PROGRESS.md` (`[ ]` → `[x]`) and add a short Work Log entry
10. **ATOMIC COMMIT** and **PUSH**
11. Exit

Do not batch tasks.

---

## Critical Review Prompt (MANDATORY)

Before changing code based on the debt deck:

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

## Stop Conditions (Escalate, Don’t Thrash)

Stop and request human input if:

1. The debt deck is inaccurate or contradicts the codebase SSOT.
2. The task would require >10 files or >500 LOC changes in a single iteration.
3. `make ci` fails after 3 attempts for the same root cause.
4. A required external tool/dep is missing and cannot be installed from the spec (e.g., optional extras not present).

If you stop:
- write a bug deck in `docs/bugs/`
- add a new unchecked item to `PROGRESS.md`
- commit and exit

---

## Quality Gates (MUST PASS)

Before marking ANY task complete:

```bash
make ci
```

---

## Git Rules (Non-Negotiable)

- Never `git rebase`
- Never `git pull`
- Never `git merge`

If push fails due to divergence:

```bash
git push --force-with-lease
```

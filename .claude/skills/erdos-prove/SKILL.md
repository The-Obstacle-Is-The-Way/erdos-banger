---
name: erdos-prove
description: Step-by-step workflow for proving an Erdos problem in Lean 4 using Claude Code/Codex (subscription-first). Invoke as /erdos-prove <problem-id>.
user-invocable: true
---

# Erdos Problem Proving Workflow

**Target Problem:** $ARGUMENTS

> **Tip:** If no problem ID provided, check `CANDIDATES.md` for the current focus problem (see Decision Log).

This workflow helps you prove Erdos problems in Lean 4 using your Claude Code/Codex subscription instead of paid API calls.

## Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│                    COST-FREE PROVING WORKFLOW                   │
├─────────────────────────────────────────────────────────────────┤
│  1. Understand   → Read problem statement           (FREE)      │
│  2. Research     → Gather literature context        (FREE)      │
│  3. Formalize    → Generate Lean skeleton           (FREE)      │
│  4. Prove        → Work with Claude Code            (SUB)       │
│  5. Verify       → Check Lean compilation           (FREE)      │
│  6. Iterate      → Fix errors with Claude Code      (SUB)       │
└─────────────────────────────────────────────────────────────────┘
```

## Step 1: Understand the Problem

First, let me read the problem statement and understand what we're trying to prove.

**Action:** I will read the problem details using:
- `data/problems_enriched.yaml` (if present) or `src/erdos/data/problems_enriched.yaml` (built-in sample dataset)
- `erdos show $ARGUMENTS` output for formatted display

**Questions to answer:**
- What is the mathematical statement?
- What is the current status (open, partially solved)?
- Are there any known partial results?

## Step 2: Research Existing Literature

Gather context from existing references without making API calls.

**Local sources (FREE):**
- `literature/manifests/$(printf '%04d' $ARGUMENTS).yaml` - Reference metadata (IDs are zero-padded, e.g. 6 → 0006.yaml)
- `literature/cache/` - Downloaded papers and sources
- `research/problems/$(printf '%04d' $ARGUMENTS)/` - Research workspace (leads, hypotheses, tasks)
- Search index: `uv run erdos search "relevant terms" --problem $ARGUMENTS` (omit `--problem` to search globally)

**Optional API sources (rate-limited, mostly free):**
- `uv run erdos refs zbmath --msc <relevant-code>` - zbMATH (free)
- `uv run erdos refs s2 citations <doi>` - Semantic Scholar (rate-limited)
- `uv run erdos ingest $ARGUMENTS --source openalex` - Fetch refs by DOI/arXiv ID (free)

**Optional AI-powered discovery (PAID):**
- `uv run erdos research exa search $ARGUMENTS "relevant query" --save-leads` - Exa AI search

## Step 3: Generate Lean Skeleton

Create the formal statement file:

```bash
uv run erdos lean formalize $ARGUMENTS
```

This creates: `formal/lean/Erdos/Problem$(printf '%03d' $ARGUMENTS).lean` (IDs are zero-padded, e.g. 6 → Problem006.lean)

**What this generates:**
- Import statements for Mathlib
- Formal theorem statement (with `sorry` placeholder)
- Comments with problem context

## Step 4: Develop the Proof (SUBSCRIPTION)

Now we work together to fill in the proof. This is where your subscription pays off instead of API calls.

**I will directly edit these files (no copy/paste needed):**
- `formal/lean/Erdos/Problem$(printf '%03d' $ARGUMENTS).lean` - The main proof file
- `data/problems_enriched.yaml` - Update status when solved

**My workflow:**
1. Read the generated Lean file
2. Analyze the theorem statement
3. Propose proof strategies
4. Write Lean tactics step by step
5. **Edit the file directly** - you just watch and run `lean check`

**Proof development strategies:**
- Break into lemmas if complex
- Use Mathlib tactics (`simp`, `ring`, `norm_num`, `omega`)
- Apply relevant theorems from Mathlib
- Build incrementally, checking each step

## Step 5: Verify Compilation

Check that the proof compiles:

```bash
PROBLEM3=$(printf '%03d' $ARGUMENTS)
uv run erdos lean check "formal/lean/Erdos/Problem${PROBLEM3}.lean"
```

**Possible outcomes:**
- **Success:** Proof compiles, no `sorry` remaining
- **Errors:** Type mismatches, tactic failures, missing imports
- **Warnings:** Unused variables, style issues

## Step 6: Iterate on Errors (SUBSCRIPTION)

When compilation fails, show me the error output and I'll:
1. Diagnose the issue
2. Propose fixes
3. Edit the file directly
4. Repeat until it compiles

**Common fixes:**
- Import missing Mathlib modules
- Adjust tactic arguments
- Add intermediate steps
- Fix type annotations

## Workflow Commands Reference

```bash
# Generate skeleton (if not done)
uv run erdos lean formalize $ARGUMENTS

# Check compilation
PROBLEM3=$(printf '%03d' $ARGUMENTS)
uv run erdos lean check "formal/lean/Erdos/Problem${PROBLEM3}.lean"

# View problem details
uv run erdos show $ARGUMENTS

# Search related literature
uv run erdos search "relevant terms" --problem $ARGUMENTS  # omit --problem to search globally

# Check formalization status
uv run erdos lean status $ARGUMENTS

# View execution logs
uv run erdos logs --problem-id $ARGUMENTS
```

## What I Can Do For You

**Read & Analyze:**
- Problem statements from YAML
- Lean files (existing proofs, Mathlib source)
- Literature (PDFs, markdown)
- Error messages

**Edit & Write:**
- Lean proof tactics
- Helper lemmas
- Type annotations
- Import statements

**Research:**
- Find relevant Mathlib theorems
- Explore proof strategies
- Identify useful tactics

## Example Conversation

```text
You: /erdos-prove 6

Claude: Let me start the proving workflow for Problem 6.

[Step 1] Reading problem statement...
Problem 6 is about... [explains math]

[Step 2] Checking existing literature...
Found 3 references in the manifest: [lists them]

[Step 3] I see formal/lean/Erdos/Problem006.lean exists. Let me read it...
Current state: Has `sorry` at line 42.

[Step 4] Here's my proposed proof approach:
1. We can use the pigeonhole principle
2. Apply Mathlib's Finset.card_le_card
3. Conclude with norm_num

Let me edit the file to add the proof...
[Makes edit]

[Step 5] Now run: uv run erdos lean check formal/lean/Erdos/Problem006.lean

You: [pastes error output]

Claude: I see the issue - we need to import Data.Nat.Prime.
Let me fix that...
[Makes edit]

Try again: uv run erdos lean check formal/lean/Erdos/Problem006.lean
```

## Why This Saves Money

| Traditional Approach | Subscription Approach |
|---------------------|----------------------|
| `erdos loop run 6` | Work with Claude Code |
| ~$0.50-5.00 per run | $0 (subscription) |
| Automated but costly | Interactive but free |
| Limited iterations | Unlimited iterations |

## Alternative: Aristotle API (Paid)

If you prefer hands-off automated proving via Harmonic's Aristotle API:

```bash
# 1. Install aristotlelib
uv sync --extra aristotle

# 2. Set API key (use export for direct CLI calls)
export ARISTOTLE_API_KEY=arstl-your-key

# 3. Run via erdos wrapper (recommended - auto-loads .env)
uv run erdos lean prove formal/lean/Erdos/Problem006.lean \
    --output formal/lean/Erdos/Problem006_aristotle.lean

# Or direct CLI (requires exported env var)
uv run aristotle prove-from-file \
    formal/lean/Erdos/Problem006.lean \
    --output-file formal/lean/Erdos/Problem006_aristotle.lean
```

**Cost:** Paid per-problem. Use the subscription workflow above for unlimited iterations.

## Ready to Begin?

Tell me to start and I'll begin Step 1: reading and understanding Problem $ARGUMENTS.

Or if you want to jump to a specific step:
- "Skip to step 3, the skeleton already exists"
- "Start from step 4, I have the Lean file ready"
- "I have errors, help me with step 6"

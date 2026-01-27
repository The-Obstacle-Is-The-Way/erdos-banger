# BUG-049: Aristotle CLI Integration Friction

**Status:** Fixed
**Severity:** Medium (blocks Aristotle usage)
**Discovered:** 2026-01-27
**Fixed:** 2026-01-27
**Component:** `erdos lean prove`, Aristotle integration

## Summary

Multiple friction points prevent smooth invocation of Aristotle API via `erdos lean prove`:

1. `aristotlelib` not in dependencies
2. `--formal-input-context` flag mismatch (boolean vs path)
3. Environment variable not passed to subprocess
4. Skill documentation doesn't cover Aristotle fallback

## What Is What?

| Component | Owner | Purpose |
|-----------|-------|---------|
| `erdos lean prove` | Us (erdos-banger) | Wrapper CLI command |
| `aristotle prove-from-file` | Harmonic (aristotlelib) | Actual prover CLI |
| `/erdos-prove` skill | Us | Subscription-first workflow (NO Aristotle) |
| `aristotlelib` | Harmonic | Python package with `aristotle` CLI |

## Friction Points

### 1. Missing Dependency

**File:** `pyproject.toml`

**Issue:** `aristotlelib` is NOT listed in dependencies. Users must manually install it.

**Error:**
```
Error: Aristotle command not found: aristotle. Ensure aristotlelib is installed
(pip install aristotlelib) or set ERDOS_ARISTOTLE_COMMAND to the correct path.
```

**Fix:** Add to optional dependencies:
```toml
[project.optional-dependencies]
aristotle = [
    "aristotlelib>=0.7.0",
]
```

Then: `uv sync --extra aristotle`

### 2. Flag Signature Mismatch

**File:** `src/erdos/core/lean/aristotle.py:213-214`

**Issue:** Our CLI treats `--formal-input-context` as a boolean flag, but Aristotle's CLI expects a PATH argument.

**Our code:**
```python
if config.formal_input_context:
    cmd.append("--formal-input-context")  # Missing path!
```

**Aristotle's actual signature:**
```
--formal-input-context FORMAL_INPUT_CONTEXT
                        Path to a Lean file containing formal context
```

**Error:**
```
aristotle prove-from-file: error: argument --formal-input-context: expected one argument
```

**Fix:** Change from boolean to optional Path:
```python
formal_input_context: Path | None = None  # instead of bool
...
if config.formal_input_context:
    cmd.extend(["--formal-input-context", str(config.formal_input_context)])
```

### 3. Environment Variable Not Inherited — ROOT CAUSE FOUND

**Issue:** When running `source .env && uv run aristotle ...`, the ARISTOTLE_API_KEY isn't visible to the subprocess.

**Error:**
```
ERROR - API key not set. Please set the ARISTOTLE_API_KEY environment variable
```

## THE CONCRETE ROOT CAUSE

The `.env` file uses plain assignment:
```bash
ARISTOTLE_API_KEY=arstl-xxx
```

**WITHOUT the `export` keyword**, this creates a **shell variable**, NOT an **environment variable**.

```bash
$ source .env
$ echo $ARISTOTLE_API_KEY     # Works (shell var)
arstl-xxx
$ env | grep ARISTOTLE        # Empty! (not in environment)
(nothing)
```

**Child processes only inherit environment variables, not shell variables.**

So when you run:
```bash
source .env && uv run aristotle ...
```

The `aristotle` subprocess cannot see `ARISTOTLE_API_KEY` because it was never exported.

## Why `erdos lean prove` Works (Sometimes)

When you run `uv run erdos lean prove ...`:
1. The erdos CLI calls `initialize_environment()` in `cli.py:103`
2. This calls `_load_dotenv_if_enabled()` which reads `.env` and sets vars via `os.environ[key] = value`
3. The vars ARE in the environment for any subprocess erdos spawns

**So the erdos wrapper works correctly.** The issue only appears when calling `aristotle` CLI directly.

## Why This Keeps Happening

1. User runs `source .env` thinking it exports vars (it doesn't without `export`)
2. User runs `uv run aristotle ...` directly (bypassing erdos)
3. The subprocess can't see the vars
4. User blames the erdos CLI or uv, but the real issue is the `.env` format

## Correct Workarounds

**Option A: Use set -a (auto-export)**
```bash
set -a           # Enable auto-export
source .env      # All assignments become exports
set +a           # Disable auto-export

uv run aristotle prove-from-file ...   # Now works!
```

**Option B: Pass --api-key explicitly**
```bash
source .env
uv run aristotle prove-from-file ... --api-key "$ARISTOTLE_API_KEY"
```

**Option C: Use erdos wrapper (recommended)**
```bash
uv run erdos lean prove ...   # Loads .env automatically
```

**Option D: Add export to .env**
```bash
# In .env:
export ARISTOTLE_API_KEY=arstl-xxx
```

## Permanent Fix Options

| Fix | Pros | Cons |
|-----|------|------|
| Add `export` to `.env.example` | Simple, clear | Breaks bash scripts that expect non-export |
| Document `set -a` pattern | No file changes | Users must remember |
| Add `--api-key` flag to erdos | Explicit control | More typing |
| Wrapper script in `scripts/` | One command | Another file to maintain |

**Recommended:** Update `.env.example` to use `export` syntax and document the `set -a` pattern in README.

### 4. Skill Documentation Gap

**File:** `.claude/skills/erdos-prove/SKILL.md`

**Issue:** The `/erdos-prove` skill is explicitly for the subscription-first workflow. It doesn't mention Aristotle at all. This is correct by design, but causes confusion.

**User confusion:** "Isn't there a way to just send it to Aristotle?"

**Fix:** Add a note to the skill:
```markdown
## When to Use Aristotle Instead

If you prefer to use the Aristotle API (paid per-problem, but hands-off):

```bash
# Ensure aristotlelib is installed
uv sync --extra aristotle

# Send to Aristotle
source .env  # or export ARISTOTLE_API_KEY=...
uv run aristotle prove-from-file \
    formal/lean/Erdos/ProblemXXX.lean \
    --output-file formal/lean/Erdos/ProblemXXX_aristotle.lean \
    --api-key "$ARISTOTLE_API_KEY"
```

This is a paid API call. The subscription workflow (above) is recommended.
```

## Correct Invocation (Today)

Until fixes are applied, use the Aristotle CLI directly:

```bash
# 1. Install aristotlelib
uv pip install aristotlelib

# 2. Source API key
source .env

# 3. Run from formal/lean directory
cd formal/lean

# 4. Invoke Aristotle directly (not through erdos wrapper)
uv run aristotle prove-from-file \
    Erdos/Problem848_COMPLETE.lean \
    --output-file Erdos/Problem848_ARISTOTLE_OUTPUT.lean \
    --api-key "$ARISTOTLE_API_KEY" \
    --polling-interval 15
```

## Files to Modify

| File | Change |
|------|--------|
| `pyproject.toml` | Add `aristotlelib` to optional deps |
| `src/erdos/core/lean/aristotle.py` | Fix `--formal-input-context` to accept Path |
| `src/erdos/commands/lean/prove_cmd.py` | Update flag type from bool to Path |
| `.claude/skills/erdos-prove/SKILL.md` | Add Aristotle fallback section |
| `.codex/skills/erdos-prove/SKILL.md` | Same (if exists) |

## Acceptance Criteria

- [x] `uv sync --extra aristotle` installs aristotlelib (add to pyproject.toml)
- [x] `erdos lean prove --formal-input-context <path>` works correctly (change flag type)
- [x] `erdos lean prove` reads ARISTOTLE_API_KEY from `.env` automatically (already works!)
- [x] Skills mention Aristotle as fallback option
- [x] `.env.example` updated with `export` and documents the pattern
- [ ] README mentions the shell vs env var distinction (OPTIONAL: info already in .env.example)
- [ ] This friction report is archived after fixes

## Related: Previous "Fixes" That Didn't Stick

This issue has been "fixed" before but keeps recurring because:

1. The erdos CLI DOES load `.env` correctly via `initialize_environment()`
2. But when users bypass erdos and call vendor CLIs directly, they hit the shell/env var distinction
3. The distinction is subtle (no error until subprocess runs) so it's easy to forget

**The real fix is documentation + `.env.example` using `export`.**

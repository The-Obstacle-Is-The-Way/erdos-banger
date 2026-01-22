# DEBT-058: `core/loop.py` Uses MD5 With `# noqa: S324` (Needs Justification or Safer Hash)

**Status:** Fixed
**Priority:** P3
**Found:** 2026-01-22
**Found By:** Security lint / Clean Code audit
**Fixed In:** 3891aeb

---

## Summary

`src/erdos/core/loop.py` uses `hashlib.md5(...)` with `# noqa: S324` in two places:

- generating a run id suffix
- hashing file content

Even if this is "non-security" use, the suppression is a red flag for reviewers and contradicts the repo's stated preference: **either remove the suppression by using a safer primitive, or document the threat model explicitly**.

---

## Evidence

- Reproduce: `rg -n "S324" src/erdos/core/loop.py`
- Current call sites:
  - `src/erdos/core/loop.py:250` (`_generate_run_id`)
  - `src/erdos/core/loop.py:257` (`_file_hash`)

---

## Why This Matters

- **Security posture:** `# noqa: S324` requires every reviewer to re-justify why MD5 is acceptable here.
- **Clean Code:** "noisy exceptions" become precedent; the next contributor copies the pattern for a worse use case.
- **Consistency:** elsewhere (`run_logger.generate_run_id`) we already use `secrets.token_hex`, which avoids this entire class of issue.

---

## Recommended Fix (Pick One)

### Option A (Recommended): Replace MD5 with a safe primitive (no suppression needed)

- Use `secrets.token_hex(3)` for run id suffixes (already used elsewhere).
- Use `hashlib.sha256(...)` for file hashes (fast enough at our file sizes).

### Option B: Keep MD5 but add explicit threat-model justification

If MD5 is kept for performance:
- add a comment explaining it is a non-security cache key and why collisions are acceptable
- keep `# noqa: S324` but make the intent explicit

---

## Acceptance Criteria

1. [x] There is no `# noqa: S324` in `src/erdos/core/loop.py` without an explicit justification comment.
2. [x] Run ids remain stable-format and unique enough for log filenames.
3. [x] `make ci` passes.

---

## Resolution

Applied Option A (Recommended):
- Replaced `hashlib.md5(str(now.timestamp()).encode()).hexdigest()[:6]` with `secrets.token_hex(3)` in `_generate_run_id()`
- Replaced `hashlib.md5(content.encode()).hexdigest()` with `hashlib.sha256(content.encode()).hexdigest()` in `_file_hash()`
- Added `import secrets` to module imports
- No more `# noqa: S324` suppressions in the file

---

## Non-Goals

- Changing loop behavior or log schema.
- Introducing cryptographic security guarantees (this is about clarity + removing lint suppressions).

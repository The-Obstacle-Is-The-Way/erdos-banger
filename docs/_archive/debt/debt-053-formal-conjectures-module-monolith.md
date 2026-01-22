# DEBT-053: `core/formal_conjectures.py` Is a Monolith (Parsing + Networking + Caching + Provenance)

**Status:** Fixed
**Priority:** P3
**Found:** 2026-01-22
**Found By:** SRP / cohesion audit
**Fixed In:** 1da90e7

---

## Summary

`src/erdos/core/formal_conjectures.py` is a large "integration module" that currently owns multiple responsibilities:

- parsing upstream metadata from `teorth/erdosproblems`
- constructing remote URLs and local paths
- fetching upstream Lean files over HTTP (with retry)
- caching remote files on disk
- detecting `sorry`/`admit` in Lean files
- tracking provenance in YAML (schema + IO)

All of this is related to "formal conjectures integration", but it still violates SRP at the module level: there are many unrelated reasons to change (schema changes, network policy changes, path layout changes, provenance format changes).

---

## Evidence

- File size: `wc -l src/erdos/core/formal_conjectures.py` → **482** lines
- The module includes hard-coded upstream constants:
  - `FORMAL_CONJECTURES_REPO`
  - `FORMAL_CONJECTURES_BASE_URL`
  - Reproduce: `rg -n "FORMAL_CONJECTURES_(REPO|BASE_URL)" src/erdos/core/formal_conjectures.py`

---

## Why This Matters

- **SRP:** a change to provenance YAML format should not require touching HTTP fetch logic.
- **DIP:** the module depends directly on `requests` and filesystem layout; swapping fetch/caching policy is hard to test.
- **Testability:** deterministic unit tests become "integration-ish" because concerns are interleaved.

---

## Recommended Fix (Package Extraction + Ports)

Extract into a bounded-context package and keep a compatibility shim:

```text
src/erdos/core/formal_conjectures/
├── __init__.py
├── config.py          # repo/url + cache path policy
├── upstream.py        # parse upstream problems.yaml formalized metadata
├── fetch.py           # fetch + cache remote .lean file (depends on retry/http port)
├── local.py           # local file inspection (sorry/admit detection, sha256)
├── provenance.py      # ProvenanceFile model + YAML IO
└── paths.py           # path helpers for cache + local file mapping
```

Keep `src/erdos/core/formal_conjectures.py` as a shim re-exporting public names for one release.

Optional improvement (future): abstract HTTP + filesystem behind ports so tests can run without touching disk/network.

---

## Acceptance Criteria

1. [x] Public imports remain stable (shim allowed).
2. [x] Network fetch logic is isolated from provenance IO.
3. [x] Unit tests exist for:
   - `has_sorry()` detection (comments + edge cases)
   - provenance load/save roundtrip
   - URL/path construction
4. [x] `make ci` passes.

---

## Resolution

Extracted `formal_conjectures.py` (482 LOC) into bounded-context package `src/erdos/core/formal_conjectures/`:

| Module | LOC | Responsibility |
|--------|-----|---------------|
| `config.py` | 19 | Constants + error class |
| `paths.py` | 59 | URL building + cache/local path helpers |
| `upstream.py` | 106 | Parse upstream formalization metadata |
| `fetch.py` | 106 | Network fetch + cache logic |
| `local.py` | 93 | Sorry detection + SHA-256 hashing |
| `provenance.py` | 110 | ProvenanceFile model + YAML IO |
| `__init__.py` | 63 | Re-exports for backward compatibility |

**Total: 556 LOC** (across 7 files vs 482 LOC in 1 file)

Public API unchanged - all imports via `from erdos.core.formal_conjectures import ...` work identically.

37 existing unit tests pass, covering all acceptance criteria.

---

## Non-Goals

- Changing upstream repo or file naming conventions.
- Adding new formalization sources beyond `formal-conjectures`.

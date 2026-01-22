# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

CLI toolkit for collaborative research on Erdős problems (1,135 curated math problems). Pipeline: problem data → literature ingestion → FTS5 search → RAG Q&A → Lean 4 formalization.

## Build & Development Commands

```bash
# Setup (requires uv: https://docs.astral.sh/uv/)
git submodule update --init --recursive
uv sync

# Run CLI
uv run erdos --version
uv run erdos list --status open --limit 5
uv run erdos show 6

# Full CI check (run before every commit)
make ci                    # format-check + lint + typecheck + cov + audit

# Individual checks
make lint                  # ruff check
make format                # ruff format
make typecheck             # mypy src/ tests/
make test                  # pytest (skip Lean + network)
make test-all              # pytest (all tests)
make smoke                 # CLI smoke test
make audit                 # LOC guardrails check
```

## Running Tests

```bash
# Fast tests (default, excludes Lean and network)
uv run pytest -m "not requires_lean and not requires_network"

# Single test file
uv run pytest tests/unit/test_models.py

# Single test function
uv run pytest tests/unit/test_models.py::test_specific_function -v

# With coverage
uv run pytest --cov=erdos --cov-fail-under=80 -m "not requires_lean and not requires_network"

# Run Lean-dependent tests (requires elan installed)
uv run pytest -m "requires_lean"
```

## Architecture

```text
src/erdos/
├── cli.py              # Typer entry point, global flags (--json, --log-level)
├── commands/           # CLI subcommands (list, show, refs, search, lean, ingest, ask)
│   ├── presenter.py    # Shared output formatting (exit_with_result, CLIOutput)
│   └── *.py           # Each command module (list_cmd.py, show.py, etc.)
└── core/               # Business logic
    ├── models/         # Pydantic models (ProblemRecord, ReferenceRecord, CLIOutput, etc.)
    ├── ask/            # RAG Q&A logic (retrieval, prompt, llm, service)
    ├── ingest/         # Reference ingestion (fetch, manifest models, service)
    ├── ports.py        # Protocol “ports” for dependency inversion
    ├── context.py      # AppContext composition root (wiring concrete deps)
    ├── exit_codes.py   # ExitCode enum
    ├── constants.py    # Shared constants (timeouts, preview lengths, limits)
    ├── timing.py       # measure_time_ms() context manager
    ├── problem_loader.py  # Loads problems from YAML
    ├── search_index.py    # SQLite FTS5 search
    ├── index_builder.py   # Index build orchestration
    ├── lean_runner.py     # Lean 4 compilation wrapper
    ├── literature_paths.py # Literature cache/manifests paths
    ├── crossref_client.py # Crossref API client
    └── arxiv_client.py    # arXiv API client
```

**Data flow:** Commands → Core functions → ProblemLoader/SearchIndex → Storage

**Key patterns:**
- Commands get dependencies via `erdos.commands.app_context.get_app_context()` (AppContext + Protocol ports)
- All commands support `--json` for machine-readable output via `CLIOutput`
- Exit codes defined in `core/exit_codes.py` (ExitCode enum)
- Tests use `tests/fixtures/sample_problems.yaml` as test data

## Data Locations

- `data/problems_enriched.yaml` - Local enriched problem dataset (titles, statements, references) (gitignored)
- `src/erdos/data/problems_enriched.yaml` - Built-in sample dataset shipped with the package
- `data/erdosproblems/` - Upstream submodule (metadata only, do not modify)
- `literature/manifests/` - Reference metadata per problem
- `literature/cache/` - arXiv source tarballs (gitignored)
- `index/` - SQLite FTS5 index (gitignored)
- `formal/lean/` - Lean 4 project

## Ralph Wiggum Logs

- Per-iteration logs are written under `logs/ralph/` (gitignored; safe to delete between runs).
- Never include API keys or other secrets in tracked files (docs, specs, prompts, etc.). `.env` is gitignored by design.

## Test Markers

```python
@pytest.mark.requires_lean    # Needs elan/Lean installed
@pytest.mark.requires_network # Needs network access
@pytest.mark.slow            # Long-running tests
@pytest.mark.e2e             # End-to-end tests
```

## Code Style

- Python 3.11+, strict mypy typing
- ruff for linting/formatting (configured in pyproject.toml)
- 80% minimum test coverage enforced
- All CLI output through Rich console or `exit_with_result()`
- Clean Code / SOLID: keep Typer callbacks thin, move orchestration into `src/erdos/core/`, and avoid growing new "god modules". If a necessary refactor is too large for the current change, create a debt deck in `docs/debt/` with evidence + acceptance criteria.

## Code Health Guardrails

CI enforces LOC (lines of code) thresholds to prevent god-file regressions:

| Scope | Threshold | Rationale |
|-------|-----------|-----------|
| Command modules (`commands/**/*.py`) | 400 LOC | Keep Typer callbacks thin |
| Core modules (`core/**/*.py`) | 500 LOC | Business logic may be denser |
| Functions | 120 LOC | Readable, testable units |

**Existing violations are exempted** if paired with a debt deck. Run `make audit` to check.

**To add an exemption:**
1. Create a debt deck in `docs/debt/debt-XXX-*.md` documenting the issue
2. Add the module/function to `EXEMPTED_MODULES` or `EXEMPTED_FUNCTIONS` in `scripts/audit_code_health.py`

**Inline exemption markers** (alternative to hardcoding):
- Module: Add `# exempt: DEBT-XXX` in the first 50 lines
- Function: Add `# exempt: DEBT-XXX` in the docstring

## Core Package Boundaries

`src/erdos/core/` uses **bounded contexts** (subpackages) to organize code by domain:

**Bounded-context subpackages:**
- `ask/` - RAG Q&A logic (retrieval, prompt, LLM, service)
- `batch/` - Batch processing (filters, state, runner)
- `clients/` - HTTP client adapters (arXiv, Crossref, OpenAlex APIs)
- `formal_conjectures/` - Lean formalization upstream sync (provenance, fetch, local)
- `ingest/` - Reference ingestion (fetch, manifest models, service)
- `loop/` - Iterative proof loop (config, verifier, patch validator, runner, prompt)
- `models/` - Pydantic domain models (ProblemRecord, ReferenceRecord, CLIOutput, etc.)
- `pdf/` - PDF conversion utilities (Marker, pdfplumber)
- `providers/` - Metadata provider implementations (arXiv, Crossref, OpenAlex, fallback)
- `search/` - Search domain (FTS, semantic, hybrid, embeddings, index builder)

**Top-level modules (stable contracts & utilities):**
- `ports.py`, `repositories.py` - Protocol "ports" and in-memory implementations for dependency inversion
- `context.py`, `config.py` - AppContext composition root and centralized configuration
- `constants.py`, `timing.py`, `exit_codes.py` - Shared utilities
- `problem_loader.py`, `literature_paths.py` - Data loading and path conventions
- `lean_runner.py`, `formalizer.py`, `aristotle.py` - Lean 4 compilation, skeleton generation, and Aristotle prover
- `rate_limiter.py`, `retry.py` - HTTP resilience utilities
- `run_logger.py`, `run_logger_summaries.py` - Execution logging

**Backward-compatible shims (thin re-exports):**
- `arxiv_client.py`, `crossref_client.py`, `openalex_client.py` → `clients/`
- `embeddings.py`, `index_builder.py`, `search_index.py` → `search/`
- `batch.py` → `batch/`
- `loop_config.py`, `loop_verifier.py`, `patch_validator.py` → `loop/`
- `pdf_converter.py` → `pdf/`

**Rules for new code:**
1. **No new top-level modules** at `src/erdos/core/*.py`. Place new code in an existing subpackage or create a new one for a distinct bounded context.
2. **Infrastructure adapters** (HTTP clients, external service wrappers) live in `core/clients/`.
3. **If a domain grows to 3+ related modules**, extract into a subpackage.

## Technical Debt Status

Track active technical debt in `docs/debt/README.md`. Resolved decks are archived under `docs/_archive/debt/`.

## Key Specs

- `docs/specs/master-vision.md` - Full architecture and roadmap
- `docs/_archive/specs/spec-010-ingest-command.md` - Ingest command (arXiv + Crossref)
- `docs/_archive/specs/spec-011-ask-command.md` - Ask command (RAG + LLM)

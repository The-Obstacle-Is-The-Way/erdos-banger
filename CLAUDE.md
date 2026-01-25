# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

CLI toolkit for collaborative research on Erdős problems (upstream dataset is 1,000+ problems and evolves over time). Pipeline: problem data → literature ingestion → FTS5 search → RAG Q&A → Lean 4 formalization.

## Documentation

Start at `docs/INDEX.md` for getting started, developer guides, and architecture docs.

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
make ci                    # fast checks (skips slow/Lean/network tests)
make ci-full               # full local CI (includes test-all + smoke)

# Individual checks
make lint                  # ruff check
make format                # ruff format
make typecheck             # mypy src/ tests/
make test                  # pytest (fast, skips slow/Lean/network)
make test-all              # pytest (all tests, includes slow/Lean/network)
make test-integration      # pytest tests/integration
make test-e2e              # pytest tests/e2e
make test-lean             # pytest -m "requires_lean"
make test-network          # pytest -m "requires_network"
make smoke                 # CLI smoke test
make audit                 # LOC guardrails check
```

## Running Tests

```bash
# Fast tests (default, excludes Lean and network)
uv run pytest -m "not requires_lean and not requires_network and not slow"

# Single test file
uv run pytest tests/unit/test_models.py

# Single test function
uv run pytest tests/unit/test_models.py::test_specific_function -v

# With coverage
uv run pytest --cov=erdos --cov-fail-under=80 -m "not requires_lean and not requires_network"

# Run Lean-dependent tests (requires elan installed)
uv run pytest -m "requires_lean"
```

### Lean Notes

If `make test-all` fails on `tests/integration/test_lean_runner.py::TestLeanRunnerIntegration::test_check_formal_project_compiles`,
pre-cache mathlib:

```bash
cd formal/lean
lake update
lake exe cache get
```

## Architecture

```text
src/erdos/
├── cli.py              # Typer entry point, global flags (--json, --log-level)
├── commands/           # CLI adapters (Typer + Rich)
│   ├── presenter.py    # Shared output formatting (exit_with_result, CLIOutput)
│   ├── lean/           # Lean-related subcommands (init/check/formalize/…)
│   └── *.py            # Other command modules (list/show/refs/search/ingest/ask/loop/logs/convert)
├── core/               # Business logic (bounded contexts + ports)
│   ├── models/         # Pydantic models (ProblemRecord, ReferenceRecord, CLIOutput, etc.)
│   ├── ask/            # RAG Q&A (retrieval, prompt, llm, service)
│   ├── ingest/         # Reference ingestion (fetch, models, service/app)
│   ├── search/         # FTS + semantic/hybrid search + embeddings
│   ├── loop/           # Iterative Lean proof loop (prompt/patch/verify/run)
│   ├── clients/        # HTTP clients (OpenAlex/Crossref/arXiv)
│   ├── providers/      # MetadataProvider implementations (SPEC-022)
│   ├── pdf/            # PDF conversion (Marker, pdfplumber)
│   ├── batch/          # Batch operations (filters/state/runner)
│   ├── formal_conjectures/ # Upstream sync + local provenance
│   ├── lean/           # Lean tooling (compile, skeletons, prover)
│   ├── ports.py        # Protocol “ports” for dependency inversion
│   ├── context.py      # AppContext composition root (wiring concrete deps)
│   └── …               # config/constants/exit codes/retry/logging/etc.
├── mcp/                # MCP server adapter (optional dependency)
├── services/           # Application services/use-cases (shared by adapters)
├── templates/          # Jinja2 templates (Lean skeletons, prompts)
└── data/               # Built-in sample dataset (`problems_enriched.yaml`)
```

**Data flow:** Commands → Core functions → ProblemLoader/SearchIndex → Storage

**Key patterns:**
- Commands get dependencies via `erdos.commands.app_context.get_app_context()` (AppContext + Protocol ports)
- All commands support `--json` for machine-readable output via `CLIOutput`
- Exit codes defined in `core/exit_codes.py` (ExitCode enum)
- Tests use `tests/fixtures/sample_problems.yaml` as test data

## Data Locations

- `data/problems_enriched.yaml` - Local enriched problem dataset (titles, statements, references) (gitignored)
- Created/updated by `erdos sync website` / `erdos sync all` (default location; override via `ERDOS_DATA_PATH`)
- `src/erdos/data/problems_enriched.yaml` - Built-in sample dataset shipped with the package
- `data/erdosproblems/` - Upstream submodule (metadata only, do not modify)
- `literature/manifests/` - Reference metadata per problem
- `literature/cache/` - arXiv source tarballs (gitignored)
- `index/` - SQLite FTS5 index (gitignored)
- `formal/lean/` - Lean 4 project

## Ralph Wiggum Loop (Autonomous Development)

The Ralph Wiggum technique runs the same prompt repeatedly until all tasks complete. State lives in files, not context.

```bash
# Launch in tmux (recommended)
tmux new-session -s erdos-ralph './scripts/ralph-loop.sh'

# Monitor in another terminal
tail -f logs/ralph/iteration_*.log
watch -n5 'git log --oneline -5'
```

**Key files:**
- `PROMPT.md` - Instructions read each iteration
- `PROGRESS.md` - Task queue (checkboxes are state)
- `docs/_ralphwiggum/protocol.md` - Full protocol

**Logs:** Per-iteration logs written to `logs/ralph/` (gitignored; safe to delete between runs).

**Security:** Never include API keys in tracked files. `.env` is gitignored.

## Test Markers

```python
@pytest.mark.requires_lean    # Needs elan/Lean installed
@pytest.mark.requires_network # Needs network access
@pytest.mark.slow            # Long-running tests
@pytest.mark.e2e             # End-to-end tests
```

## Testing Gotchas

### CLI Help Output & ANSI Codes

**Problem:** Typer/Rich emit ANSI escape codes (`\x1b[1m`) in CI when `PY_COLORS=1` is set. Tests asserting on `--help` output fail with:
```
AssertionError: assert '--flag' in '\x1b[1m-\x1b[0m\x1b[1m-flag\x1b[0m'
```

**Solution:** Always use the `strip_ansi` fixture from `tests/conftest.py`:
```python
def test_help_shows_flag(strip_ansi: Callable[[str], str]) -> None:
    result = runner.invoke(app, ["command", "--help"])
    output = strip_ansi(result.output)  # Normalize ANSI codes
    assert "--flag" in output
```

**Why:** `conftest.py` already unsets `PY_COLORS` before Rich imports, but this doesn't cover all edge cases. The fixture is the defensive pattern.

### External Repository Dependencies

**Problem:** Tests that clone external repos (e.g., Lean libraries) break when repos are renamed or restructured.

**Examples:**
- `leanprover/std4` → `leanprover-community/batteries` (2024)
- `lakefile.lean` → `lakefile.toml` (Lean 4 convention change)

**Solution:**
1. Prefer fixture repos under `tests/fixtures/` for deterministic tests
2. If you must use external repos, add a comment with DEBT ticket reference
3. Check for both old and new file conventions when asserting

### Key Test Fixtures (conftest.py)

| Fixture | Purpose |
|---------|---------|
| `strip_ansi` | Normalize CLI output for assertions |
| `sample_problem` | Minimal `ProblemRecord` instance |
| `fixtures_dir` | Path to `tests/fixtures/` |
| `sample_problems_yaml` | Path to test YAML data |
| `in_memory_db` | SQLite connection for search tests |
| `arxiv_*_fixture` | Cached arXiv API responses |
| `crossref_*_fixture` | Cached Crossref API responses |

## Code Style

- Python 3.11+, strict mypy typing
- ruff for linting/formatting (configured in pyproject.toml)
- 80% minimum test coverage enforced
- All CLI output through Rich console or `exit_with_result()`
- Clean Code / SOLID: keep Typer callbacks thin, move orchestration into `src/erdos/core/`, and avoid growing new "god modules". If a necessary refactor is too large for the current change, create a debt deck in `docs/_debt/` with evidence + acceptance criteria.

## Code Health Guardrails

CI enforces LOC (lines of code) thresholds to prevent god-file regressions:

| Scope | Threshold | Rationale |
|-------|-----------|-----------|
| Command modules (`commands/**/*.py`) | 400 LOC | Keep Typer callbacks thin |
| Core modules (`core/**/*.py`) | 500 LOC | Business logic may be denser |
| Functions | 120 LOC | Readable, testable units |

**Existing violations are exempted** if paired with a debt deck. Run `make audit` to check.

**To add an exemption:**
1. Create a debt deck in `docs/_debt/debt-XXX-*.md` documenting the issue
2. Add the module/function to `EXEMPTED_MODULES` or `EXEMPTED_FUNCTIONS` in `scripts/audit_code_health.py`

**Inline exemption markers** (alternative to hardcoding):
- Module: Add `# exempt: DEBT-XXX` in the first 50 lines
- Function: Add `# exempt: DEBT-XXX` in the docstring

## Core Package Boundaries

`src/erdos/core/` uses **bounded contexts** (subpackages) to organize code by domain:

**Bounded-context subpackages:**
- `ask/` - RAG Q&A logic (retrieval, prompt, LLM, service)
- `batch/` - Batch processing (filters, state, runner)
- `clients/` - HTTP client adapters (arXiv, Crossref, OpenAlex, Exa, Semantic Scholar, zbMATH)
- `formal_conjectures/` - Lean formalization upstream sync (provenance, fetch, local)
- `ingest/` - Reference ingestion (fetch, manifest models, service)
- `lean/` - Lean tooling (compilation, skeleton generation, prover wrappers)
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
- `rate_limiter.py`, `retry.py` - HTTP resilience utilities
- `run_logger.py`, `run_logger_summaries.py` - Execution logging

**Backwards-compatibility note:** core-root “shim modules” were removed (DEBT-061). Prefer canonical imports from the bounded-context subpackages (e.g., `erdos.core.clients.openalex`, `erdos.core.search.*`, `erdos.core.loop.*`).

**Rules for new code:**
1. **No new top-level modules** at `src/erdos/core/*.py`. Place new code in an existing subpackage or create a new one for a distinct bounded context.
2. **Infrastructure adapters** (HTTP clients, external service wrappers) live in `core/clients/`.
3. **If a domain grows to 3+ related modules**, extract into a subpackage.

## Technical Debt Status

Track active technical debt in `docs/_debt/README.md`. Resolved decks are archived under `docs/_archive/debt/`.

## Key Specs

- `docs/_specs/master-vision.md` - Full architecture and roadmap
- `docs/_archive/specs/spec-010-ingest-command.md` - Ingest command (arXiv + Crossref)
- `docs/_archive/specs/spec-011-ask-command.md` - Ask command (RAG + LLM)

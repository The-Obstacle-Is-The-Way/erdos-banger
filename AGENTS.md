# Repository Guidelines

## Ralph Wiggum Loop (Autonomous Development)

This repo uses the **Ralph Wiggum technique** for autonomous AI development sprints.

**Core concept:** Same prompt repeated until completion. State lives in files (`PROGRESS.md`), not context.

```bash
# Launch (in tmux for persistence)
tmux new-session -s erdos-ralph './scripts/ralph-loop.sh'

# Monitor (another terminal)
tail -f logs/ralph/iteration_*.log
watch -n5 'git log --oneline -5'
```

**Key files:**
- `PROMPT.md` - Loop instructions (read each iteration)
- `PROGRESS.md` - Task queue with checkboxes (state)
- `docs/_debt/` - Active debt decks (SSOT for work)
- `logs/ralph/` - Per-iteration logs (gitignored)

**Protocol:** See `docs/_ralphwiggum/protocol.md` for full details.

---

## Project Structure

- `src/erdos/`: Python package (CLI + core logic).
  - `src/erdos/cli.py`: top-level Typer app entrypoint.
  - `src/erdos/commands/`: CLI command modules (e.g., `list_cmd.py`, `search.py`).
  - `src/erdos/core/`: core bounded contexts (e.g., `ask/`, `ingest/`, `search/`, `loop/`, `providers/`) + stable utilities (`context.py`, `ports.py`).
  - `src/erdos/services/`: application services/use-cases shared across adapters.
  - `src/erdos/mcp/`: MCP server adapter (optional dependency).
- `tests/`: pytest suite (`unit/`, `integration/`, `e2e/`) and `tests/fixtures/`.
- `docs/`: specs, ADRs, bug/debt decks, vendor docs, and process docs.
- `docs/INDEX.md`: documentation landing page (getting started, developer guides, architecture, process docs).
- `formal/lean/`: Lean 4 project scaffold used by Lean integration.
- `scripts/`: helper scripts (e.g., `scripts/smoke-test.sh`, LLM wrappers).
- `logs/ralph/`: per-iteration Ralph Wiggum logs (gitignored; safe to clear between runs).

## Build, Test, and Development Commands

Use `make` (preferred) or `uv` directly:

- `make sync`: install dependencies (uses `uv`).
- `make ci`: fast CI check (format/lint/typecheck/cov/audit). Skips `slow`/Lean/network tests.
- `make ci-full`: full local CI (includes `make test-all` + `make smoke`).
- `make test`: run fast tests (skips `slow`/Lean/network).
- `make test-all`: run all tests (includes `slow`, `requires_lean`, `requires_network`).
- `make test-integration`, `make test-e2e`, `make test-lean`, `make test-network`: focused test targets.
- `make smoke`: run CLI smoke test (`scripts/smoke-test.sh`).
- Example CLI run: `uv run erdos --help`

## Coding Style & Naming Conventions

- Python 3.11 (`.python-version`).
- Formatting/linting: Ruff (`make format`, `make lint`).
- Type checking: mypy strict (`make typecheck`).
- Prefer small, testable “core logic” helpers and thin Typer callbacks.
- Clean Code expectation: avoid “god files” and mixed responsibilities; if a refactor is too risky for the current PR, write a debt deck in `docs/_debt/` instead of piling on.
- Follow existing naming patterns (e.g., `list_()` for the reserved keyword).

## Testing Guidelines

- Framework: pytest; markers include `e2e`, `slow`, `requires_lean`, `requires_network`.
- Coverage target: `--cov-fail-under=80` (see `make cov`).
- New features should include unit tests and (when appropriate) integration tests using `tests/fixtures/`.

### API Keys for Network Tests

Tests marked `requires_network` may need API keys (e.g., `EXA_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY`).

**Local development:** Create a `.env` file in the project root with your keys:
```bash
EXA_API_KEY=your-key-here
SEMANTIC_SCHOLAR_API_KEY=your-key-here
```
The `.env` file is gitignored and loaded automatically by `pytest-dotenv`.

**CI:** API keys are injected as environment variables by GitHub Actions secrets.

**No key?** Tests skip gracefully with "KEY not set" messages.

### Testing Gotchas

**ANSI escape codes in CLI output:**
- Rich/Typer emit ANSI codes in CI (`PY_COLORS=1`)
- Tests asserting on `--help` output MUST use the `strip_ansi` fixture:
  ```python
  def test_help(strip_ansi: Callable[[str], str]) -> None:
      result = runner.invoke(app, ["cmd", "--help"])
      assert "--flag" in strip_ansi(result.output)
  ```

**External repo dependencies:**
- Tests cloning external repos (e.g., Lean libraries) can break when repos rename
- Prefer `tests/fixtures/` for deterministic tests
- Add DEBT reference comments when external repos are unavoidable

**Key fixtures (conftest.py):**
- `strip_ansi` - Normalize CLI output
- `sample_problem` - Minimal ProblemRecord
- `fixtures_dir` - Path to test fixtures
- `in_memory_db` - SQLite for search tests
- `sample_problems_yaml` - Path to sample `problems_enriched.yaml` fixture
- `arxiv_*_fixture` - Cached arXiv API XML fixtures
- `crossref_*_fixture` - Cached Crossref API JSON fixtures

## Commits & Pull Requests

- Commit style: Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`), often with scopes (e.g., `fix(core): ...`).
- Before opening a PR: run `make ci` and ensure `git status` is clean.
- PRs should include a short summary, test plan, and links to relevant specs/issues. CodeRabbit reviews are enabled on PRs.

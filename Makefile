.DEFAULT_GOAL := help

UV ?= uv
RUN := $(UV) run

PYTEST_FAST_MARKERS := not requires_lean and not requires_network and not slow

# Directories to clean
CLEAN_DIRS := .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov dist build *.egg-info __pycache__ .hypothesis

.PHONY: help \
	dev setup \
	sync sync-frozen \
	lock lock-check \
	format format-check \
	lint lint-fix \
	typecheck \
	test test-all cov watch \
	pre-commit hooks \
	smoke \
	check fix \
	security \
	audit \
	clean reset \
	ci

##@ Getting Started

help: ## Show available targets
	@echo "Usage:"
	@echo "  make <target>"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*##"} /^##@/ { printf "\n%s\n", substr($$0, 5) } /^[a-zA-Z0-9_.-]+:.*##/ { printf "  %-16s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

dev: ## 🚀 One-command dev setup (new contributors start here)
	@echo "Setting up development environment..."
	git submodule update --init --recursive
	$(UV) sync
	$(RUN) pre-commit install --install-hooks
	@echo ""
	@echo "✅ Ready! Run 'make check' to verify everything works."

setup: dev ## Alias for 'make dev'

##@ Dependencies

sync: ## Install dependencies
	$(UV) sync

sync-frozen: ## Install dependencies (frozen)
	$(UV) sync --frozen

lock: ## Update uv.lock
	$(UV) lock

lock-check: ## Verify uv.lock matches pyproject.toml
	$(UV) lock --check

##@ Code Quality

format: ## Format code (ruff)
	$(RUN) ruff format .

format-check: ## Check formatting (ruff)
	$(RUN) ruff format . --check

lint: ## Lint (ruff)
	$(RUN) ruff check .

lint-fix: ## Lint and apply fixes (ruff)
	$(RUN) ruff check . --fix

typecheck: ## Type-check (mypy)
	$(RUN) mypy src/ tests/

check: format-check lint typecheck ## ⚡ Fast check (no tests)

fix: ## 🔧 Auto-fix all fixable issues
	$(RUN) ruff format .
	$(RUN) ruff check . --fix

##@ Testing

test: ## Run tests (skip Lean + network)
	$(RUN) pytest -m "$(PYTEST_FAST_MARKERS)"

test-all: ## Run all tests
	$(RUN) pytest

cov: ## Coverage (skip Lean + network)
	$(RUN) pytest --cov=erdos --cov-fail-under=80 -m "$(PYTEST_FAST_MARKERS)"

watch: ## 👀 Watch mode - rerun tests on file changes
	$(RUN) pytest-watch -- -m "$(PYTEST_FAST_MARKERS)" -x -q

##@ Git Hooks

pre-commit: ## Run all pre-commit hooks
	$(RUN) pre-commit run --all-files

hooks: ## Install git hooks (pre-commit)
	$(RUN) pre-commit install --install-hooks

##@ Security

security: ## 🔒 Run security scans (bandit)
	$(RUN) bandit -r src/ -c pyproject.toml || true
	@echo ""
	@echo "Tip: Add 'bandit' to dev dependencies if not installed"

##@ Utilities

smoke: ## Run CLI smoke test
	./scripts/smoke-test.sh

clean: ## 🧹 Remove build artifacts and caches
	rm -rf $(CLEAN_DIRS)
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".coverage*" -delete 2>/dev/null || true
	@echo "✅ Cleaned"

reset: clean ## 🔄 Nuclear option - clean everything and reinstall
	rm -rf .venv
	$(UV) sync
	$(RUN) pre-commit install --install-hooks
	@echo "✅ Fresh environment ready"

##@ Code Health

audit: ## Check code health (LOC guardrails)
	$(RUN) python scripts/audit_code_health.py

##@ CI

ci: format-check lint typecheck cov audit ## Run CI-equivalent checks

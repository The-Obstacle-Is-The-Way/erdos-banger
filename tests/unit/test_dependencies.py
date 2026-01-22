"""Tests for project dependency configuration."""

import ast
import re
import tomllib
from itertools import chain
from pathlib import Path

import requests


def test_requests_is_installed() -> None:
    """Verify requests library is installed and importable.

    This test ensures BUG-007 is fixed: requests must be in pyproject.toml
    dependencies, not just types-requests in dev dependencies.

    Relates to:
    - src/erdos/core/ingest.py (imports requests)
    - src/erdos/core/arxiv_client.py (imports requests)
    - src/erdos/core/crossref_client.py (imports requests)
    """
    # If we got here, requests imported successfully at module level
    assert requests is not None


def test_requests_version_meets_spec() -> None:
    """Verify requests version meets SPEC-010 requirement (>=2.32.5).

    SPEC-010 Section 5.0 requires requests>=2.32.5 for security fixes.
    """
    # Parse version, handling pre-release/post-release suffixes
    # e.g., "2.32.5" or "2.32.5.post1" or "2.32.5rc1" -> (2, 32, 5)
    version_str = requests.__version__
    # Extract numeric parts using regex (handles suffixes like .post1, rc1, etc.)
    match = re.match(r"(\d+)\.(\d+)\.(\d+)", version_str)
    assert match, f"Could not parse version string: {version_str}"
    version_parts = tuple(int(x) for x in match.groups())
    required = (2, 32, 5)

    assert version_parts >= required, (
        f"requests version {version_str} is below required "
        f"{'.'.join(map(str, required))}"
    )


def test_pyproject_toml_has_requests_dependency() -> None:
    """Verify pyproject.toml explicitly lists requests in dependencies.

    This prevents regression of BUG-007 where requests was imported but
    not declared as a dependency.
    """
    # Read pyproject.toml from project root
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"

    with pyproject_path.open("rb") as f:
        pyproject = tomllib.load(f)

    dependencies = pyproject.get("project", {}).get("dependencies", [])
    assert isinstance(dependencies, list)
    found_requests = any(
        isinstance(dep, str) and dep.lstrip().startswith("requests")
        for dep in dependencies
    )

    assert found_requests, (
        "requests>=2.32.5 must be in [project] dependencies section "
        "of pyproject.toml (not just in dev dependencies)"
    )


# DEBT-061 regression guards: prevent backward-compatibility shim reintroduction
#
# These modules were shim files at src/erdos/core/*.py that re-exported
# symbols from bounded-context subpackages. They were removed in DEBT-061.
# Note: "batch" is NOT included because erdos.core.batch/ is a legitimate
# subpackage (the shim file batch.py was removed earlier).
REMOVED_SHIM_MODULES = [
    "arxiv_client",
    "crossref_client",
    "openalex_client",
    "embeddings",
    "index_builder",
    "search_index",
    "pdf_converter",
    "patch_validator",
    "loop_config",
    "loop_verifier",
]


def _shim_import_violation_lines(
    node: ast.AST,
    *,
    dotted_shims: set[str],
    shim_modules: set[str],
) -> list[int]:
    linenos: list[int] = []

    if isinstance(node, ast.Import):
        if any(alias.name in dotted_shims for alias in node.names):
            linenos = [node.lineno]
    elif isinstance(node, ast.ImportFrom):
        module = node.module
        if module and (
            module in dotted_shims
            or (
                module == "erdos.core"
                and any(alias.name in shim_modules for alias in node.names)
            )
        ):
            linenos = [node.lineno]

    return linenos


def _removed_shim_import_violations(
    py_file: Path,
    *,
    project_root: Path,
    dotted_shims: set[str],
    shim_modules: set[str],
) -> list[str]:
    content = py_file.read_text(encoding="utf-8")
    rel_path = py_file.relative_to(project_root)
    try:
        tree = ast.parse(content, filename=str(py_file))
    except SyntaxError as exc:
        lineno = exc.lineno or 0
        message = exc.msg or "SyntaxError"
        return [f"{rel_path}:{lineno}: SYNTAX ERROR: {message}"]
    lines = content.splitlines()

    violations: list[str] = []

    for node in ast.walk(tree):
        for lineno in _shim_import_violation_lines(
            node,
            dotted_shims=dotted_shims,
            shim_modules=shim_modules,
        ):
            line = lines[lineno - 1].strip() if lineno <= len(lines) else ""
            violations.append(f"{rel_path}:{lineno}: {line}")

    return violations


def test_no_core_backward_compat_shim_files() -> None:
    """Ensure DEBT-061 shim files do not exist in src/erdos/core/.

    These modules were removed in DEBT-061. They re-exported symbols from
    bounded-context subpackages (clients/, search/, loop/, pdf/, batch/).
    If any exist, it indicates a regression.
    """
    core_dir = Path(__file__).parent.parent.parent / "src" / "erdos" / "core"

    for module in REMOVED_SHIM_MODULES:
        shim_path = core_dir / f"{module}.py"
        assert not shim_path.exists(), (
            f"Backward-compatibility shim {shim_path.name} still exists. "
            f"DEBT-061 required removing these shims. "
            f"Use the bounded-context module directly instead."
        )


def test_no_imports_of_removed_shim_paths() -> None:
    """Ensure no code imports the removed shim module paths.

    DEBT-061 removed these shims; all imports should use the bounded-context
    subpackages directly (e.g., erdos.core.clients.arxiv instead of
    erdos.core.arxiv_client).
    """
    project_root = Path(__file__).parent.parent.parent
    src_dir = project_root / "src"
    tests_dir = project_root / "tests"
    this_file = Path(__file__).resolve()

    # Parse imports to avoid false positives from comments/strings.
    shim_modules = set(REMOVED_SHIM_MODULES)
    dotted_shims = {f"erdos.core.{m}" for m in shim_modules}

    violations: list[str] = []

    for py_file in chain(src_dir.rglob("*.py"), tests_dir.rglob("*.py")):
        if py_file.resolve() == this_file:
            continue
        violations.extend(
            _removed_shim_import_violations(
                py_file,
                project_root=project_root,
                dotted_shims=dotted_shims,
                shim_modules=shim_modules,
            )
        )

    assert not violations, (
        f"Found {len(violations)} import(s) of removed DEBT-061 shim paths:\n"
        + "\n".join(violations[:10])  # Show first 10
        + ("\n..." if len(violations) > 10 else "")
        + "\n\nUse the bounded-context modules instead:\n"
        "  erdos.core.arxiv_client -> erdos.core.clients.arxiv\n"
        "  erdos.core.crossref_client -> erdos.core.clients.crossref\n"
        "  erdos.core.openalex_client -> erdos.core.clients.openalex\n"
        "  erdos.core.embeddings -> erdos.core.search.embeddings\n"
        "  erdos.core.index_builder -> erdos.core.search.index_builder\n"
        "  erdos.core.search_index -> erdos.core.search.facade/types\n"
        "  erdos.core.pdf_converter -> erdos.core.pdf.converter\n"
        "  erdos.core.patch_validator -> erdos.core.loop.patch_validator\n"
        "  erdos.core.loop_config -> erdos.core.loop.config\n"
        "  erdos.core.loop_verifier -> erdos.core.loop.verifier"
    )

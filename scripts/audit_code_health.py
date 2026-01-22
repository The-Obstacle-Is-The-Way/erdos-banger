#!/usr/bin/env python3
"""
Audit script for code health guardrails against god-files/god-functions.

Enforces LOC thresholds for modules and functions in commands/core directories.
Files/functions can be exempted via inline markers when paired with a debt deck.

Usage:
    python scripts/audit_code_health.py [--strict]

Exit codes:
    0: All checks pass (or only existing debt violations found)
    1: New violations detected (above thresholds without exemption)

Exemption markers:
    Module-level: Add '# exempt: DEBT-XXX' comment in docstring or top of file
    Function-level: Add '# exempt: DEBT-XXX' in function docstring

See CLAUDE.md for threshold documentation.
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterator


# Thresholds (lines of code)
MODULE_LOC_THRESHOLD_COMMANDS = 400
MODULE_LOC_THRESHOLD_CORE = 500
FUNCTION_LOC_THRESHOLD = 120

# Known exemptions paired with debt decks (module -> debt ID)
# These files are tracked for refactoring and should not trigger CI failures
EXEMPTED_MODULES: dict[str, str] = {
    "src/erdos/commands/search.py": "DEBT-043",
    "src/erdos/commands/ingest.py": "DEBT-052",
    "src/erdos/core/loop.py": "DEBT-042",
    "src/erdos/core/search_index.py": "DEBT-049",
    "src/erdos/core/batch.py": "DEBT-051",
    "src/erdos/core/formal_conjectures.py": "DEBT-053",
    "src/erdos/core/run_logger.py": "DEBT-054",
    "src/erdos/core/ingest/fetch.py": "DEBT-050",
}

# Known exemptions for long functions paired with debt decks
EXEMPTED_FUNCTIONS: dict[tuple[str, str], str] = {
    ("src/erdos/core/loop.py", "run_loop"): "DEBT-042",
    ("src/erdos/commands/search.py", "search"): "DEBT-043",
    ("src/erdos/commands/ingest.py", "ingest"): "DEBT-052",
    ("src/erdos/commands/convert.py", "convert"): "DEBT-036",
    ("src/erdos/commands/loop.py", "run"): "DEBT-042",
    ("src/erdos/core/ingest/service.py", "ingest_problem_references"): "DEBT-050",
    ("src/erdos/commands/lean/formalize_cmd.py", "register"): "DEBT-060",
    ("src/erdos/commands/lean/formalize_cmd.py", "formalize"): "DEBT-060",
}


@dataclass
class ModuleViolation:
    """A module exceeding LOC threshold."""

    path: str
    lines: int
    threshold: int
    exempted: bool = False
    debt_id: str | None = None


@dataclass
class FunctionViolation:
    """A function exceeding LOC threshold."""

    path: str
    name: str
    lineno: int
    lines: int
    threshold: int
    exempted: bool = False
    debt_id: str | None = None


def count_lines(path: Path) -> int:
    """Count total lines in a Python file."""
    try:
        content = path.read_text()
        return len(content.splitlines())
    except (OSError, UnicodeDecodeError):
        return 0


def get_functions(
    path: Path,
) -> Iterator[tuple[str, int, int, ast.FunctionDef | ast.AsyncFunctionDef]]:
    """
    Yield (function_name, start_line, line_count, node) for all functions in a file.

    Includes both regular and async functions.
    Skips nested (inner) functions.
    """
    try:
        source = path.read_text()
        tree = ast.parse(source, filename=str(path))
    except (SyntaxError, OSError, UnicodeDecodeError):
        return

    parent_map: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parent_map[child] = parent

    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.end_lineno is not None
        ):
            parent_node = parent_map.get(node)
            if isinstance(parent_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            lines = node.end_lineno - node.lineno + 1
            yield (node.name, node.lineno, lines, node)


def check_module_exemption(path_str: str, content: str) -> tuple[bool, str | None]:
    """
    Check if a module has an exemption marker.

    Returns (is_exempted, debt_id).
    """
    # Check hardcoded exemptions first
    if path_str in EXEMPTED_MODULES:
        return True, EXEMPTED_MODULES[path_str]

    # Check for inline exemption marker: # exempt: DEBT-XXX
    marker = "# exempt:"
    for line in content.splitlines()[:50]:  # Check first 50 lines
        lower = line.lower()
        if marker in lower:
            remainder = line[lower.index(marker) + len(marker) :]
            if remainder.strip():
                debt_id = remainder.strip().split()[0].upper()
                if debt_id.startswith("DEBT-"):
                    return True, debt_id
            return True, None

    return False, None


def check_function_exemption(
    path_str: str, func_name: str, node: ast.FunctionDef | ast.AsyncFunctionDef
) -> tuple[bool, str | None]:
    """
    Check if a function has an exemption marker.

    Returns (is_exempted, debt_id).
    """
    # Check hardcoded exemptions first
    key = (path_str, func_name)
    if key in EXEMPTED_FUNCTIONS:
        return True, EXEMPTED_FUNCTIONS[key]

    # Check for inline exemption in function docstring
    docstring = ast.get_docstring(node)
    if docstring:
        marker = "# exempt:"
        lower = docstring.lower()
        if marker in lower:
            idx = lower.index(marker)
            after = docstring[idx + len(marker) :]
            debt_id = after.strip().split()[0].upper() if after.strip() else ""
            if debt_id.startswith("DEBT-"):
                return True, debt_id
            return True, None

    return False, None


def audit_modules(base_path: Path) -> list[ModuleViolation]:
    """Audit all modules in commands/ and core/ for LOC violations."""
    violations: list[ModuleViolation] = []

    patterns = [
        ("src/erdos/commands/**/*.py", MODULE_LOC_THRESHOLD_COMMANDS),
        ("src/erdos/core/**/*.py", MODULE_LOC_THRESHOLD_CORE),
    ]

    for pattern, threshold in patterns:
        for path in base_path.glob(pattern):
            if path.name == "__init__.py":
                continue

            try:
                content = path.read_text()
            except (OSError, UnicodeDecodeError):
                content = ""

            lines = len(content.splitlines()) if content else 0
            if lines > threshold:
                path_str = path.relative_to(base_path).as_posix()
                exempted, debt_id = check_module_exemption(path_str, content)
                violations.append(
                    ModuleViolation(
                        path=path_str,
                        lines=lines,
                        threshold=threshold,
                        exempted=exempted,
                        debt_id=debt_id,
                    )
                )

    return violations


def audit_functions(base_path: Path) -> list[FunctionViolation]:
    """Audit all functions in commands/ and core/ for LOC violations."""
    violations: list[FunctionViolation] = []

    patterns = [
        "src/erdos/commands/**/*.py",
        "src/erdos/core/**/*.py",
    ]

    for pattern in patterns:
        for path in base_path.glob(pattern):
            if path.name == "__init__.py":
                continue

            path_str = path.relative_to(base_path).as_posix()
            for func_name, lineno, lines, node in get_functions(path):
                if lines > FUNCTION_LOC_THRESHOLD:
                    exempted, debt_id = check_function_exemption(
                        path_str, func_name, node
                    )
                    violations.append(
                        FunctionViolation(
                            path=path_str,
                            name=func_name,
                            lineno=lineno,
                            lines=lines,
                            threshold=FUNCTION_LOC_THRESHOLD,
                            exempted=exempted,
                            debt_id=debt_id,
                        )
                    )

    return violations


def print_report(
    module_violations: list[ModuleViolation],
    function_violations: list[FunctionViolation],
) -> None:
    """Print a formatted report of violations."""
    if not module_violations and not function_violations:
        print("✅ No code health violations found")
        return

    print("=" * 70)
    print("CODE HEALTH AUDIT REPORT")
    print("=" * 70)

    if module_violations:
        print("\n📁 MODULE SIZE VIOLATIONS")
        print("-" * 70)
        for mv in sorted(module_violations, key=lambda x: -x.lines):
            status = "⚠️  EXEMPT" if mv.exempted else "❌ VIOLATION"
            debt_info = f" ({mv.debt_id})" if mv.debt_id else ""
            print(f"  {status}{debt_info}")
            print(f"    {mv.path}: {mv.lines} LOC (threshold: {mv.threshold})")

    if function_violations:
        print("\n🔧 FUNCTION SIZE VIOLATIONS")
        print("-" * 70)
        for fv in sorted(function_violations, key=lambda x: -x.lines):
            status = "⚠️  EXEMPT" if fv.exempted else "❌ VIOLATION"
            debt_info = f" ({fv.debt_id})" if fv.debt_id else ""
            print(f"  {status}{debt_info}")
            print(
                f"    {fv.path}:{fv.lineno} {fv.name}(): "
                f"{fv.lines} LOC (threshold: {fv.threshold})"
            )

    print("\n" + "=" * 70)


def main() -> int:
    """
    Run the code health audit.

    Returns 0 if no unexempted violations, 1 otherwise.
    """
    parser = argparse.ArgumentParser(
        description="Audit code health (LOC thresholds for modules/functions)"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail even for exempted violations (useful for tracking progress)",
    )
    args = parser.parse_args()

    base_path = Path(__file__).parent.parent
    if (
        not base_path.joinpath("pyproject.toml").exists()
        and not base_path.joinpath("src/erdos").exists()
    ):
        print(
            f"ERROR: Could not locate repository root from {base_path}",
            file=sys.stderr,
        )
        return 1
    module_violations = audit_modules(base_path)
    function_violations = audit_functions(base_path)

    print_report(module_violations, function_violations)

    # Count unexempted violations
    unexempted_modules = [v for v in module_violations if not v.exempted]
    unexempted_functions = [v for v in function_violations if not v.exempted]

    if args.strict:
        # In strict mode, any violation (even exempted) fails
        if module_violations or function_violations:
            print(
                f"\n❌ STRICT MODE: {len(module_violations)} module + "
                f"{len(function_violations)} function violations found"
            )
            return 1
    # Normal mode: only unexempted violations fail
    elif unexempted_modules or unexempted_functions:
        print(
            f"\n❌ FAILED: {len(unexempted_modules)} module + "
            f"{len(unexempted_functions)} function violations without exemption"
        )
        print("\nTo fix:")
        print("  1. Refactor the code to reduce size, OR")
        print("  2. Create a debt deck and add exemption to this script")
        return 1

    # Report exemption count for visibility
    exempted_count = len([v for v in module_violations if v.exempted]) + len(
        [v for v in function_violations if v.exempted]
    )
    if exempted_count > 0:
        print(f"\n(i) {exempted_count} exempted violations (tracked in debt decks)")

    print("\n✅ Code health audit passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# Spec 007: Lean 4 Integration

> Defines the Lean 4 project structure, runner, error parsing, and skeleton generation for theorem formalization.

**Status:** Archived (implemented)

---

## Overview

Lean integration is core to erdos-banger: the goal is to formalize Erdős problems and attempt proofs. This spec covers:

1. Lean project structure and configuration
2. Running Lean and capturing errors
3. Parsing Lean compiler output
4. Generating Lean skeletons from problem statements

### Guiding Principles

1. **Version pinning** - Lock Lean and mathlib versions for reproducibility
2. **Structured errors** - Parse Lean output into machine-readable format
3. **Minimal templates** - Generate compilable skeletons, not complete proofs
4. **Incremental** - Check individual files, not always the full project

---

## 1) Lean Project Structure

```
formal/
└── lean/
    ├── lean-toolchain           # Lean version (managed by elan)
    ├── lakefile.lean            # Lake build configuration
    ├── lake-manifest.json       # Dependency lock file (auto-generated)
    ├── Erdos.lean               # Root module that imports all problems
    ├── Erdos/
    │   ├── Basic.lean           # Common definitions
    │   ├── Problem006.lean      # Individual problem formalizations
    │   ├── Problem067.lean
    │   └── ...
    ├── .lake/                   # Build artifacts (gitignored)
    └── lake-packages/           # Downloaded dependencies (gitignored)
```

---

## 2) Configuration Files

### lean-toolchain

```
leanprover/lean4:v4.12.0
```

This file tells elan which Lean version to use. **Important:** The toolchain version must match the mathlib4 version you're using.

**To sync with latest mathlib4:**
```bash
curl -L https://raw.githubusercontent.com/leanprover-community/mathlib4/master/lean-toolchain -o lean-toolchain
lake update
lake exe cache get  # Download precompiled mathlib (highly recommended)
```

### lakefile.lean

```lean
import Lake
open Lake DSL

package erdos where
  -- Package configuration
  leanOptions := #[
    ⟨`autoImplicit, false⟩,  -- Require explicit type annotations
    ⟨`pp.unicode.fun, true⟩  -- Pretty print with Unicode
  ]

-- Pin mathlib to a specific version for reproducibility
-- Update this version along with lean-toolchain when upgrading
require mathlib from git
  "https://github.com/leanprover-community/mathlib4.git" @ "v4.12.0"

@[default_target]
lean_lib Erdos where
  -- Library configuration
  globs := #[.submodules `Erdos]
```

**Note:** When updating mathlib, ensure `lean-toolchain` and the mathlib version are compatible. Check [mathlib4 releases](https://github.com/leanprover-community/mathlib4/releases) for version tags.

### Erdos.lean (Root Module)

```lean
-- Erdos.lean
-- Root module that imports all problem formalizations

import Erdos.Basic
-- Individual problems imported as they're created:
-- import Erdos.Problem006
-- import Erdos.Problem067
```

### Erdos/Basic.lean

```lean
-- Erdos/Basic.lean
-- Common definitions and imports for Erdős problem formalizations

import Mathlib.Data.Nat.Prime.Basic
import Mathlib.Data.Finset.Basic
import Mathlib.Algebra.BigOperators.Group.Finset
import Mathlib.Combinatorics.SimpleGraph.Basic

-- Mark this as an Erdős problem (for metadata)
structure ErdosProblem where
  id : Nat
  title : String
  status : String  -- "open", "proved", "disproved"
  deriving Repr

-- Common tactics and lemmas can be added here
```

---

## 3) Lean Runner Implementation

**SSOT:** `src/erdos/core/lean_runner.py`

Implementation notes (repo-specific):
- Uses `datetime.UTC` to satisfy Ruff `UP017`
- Uses `TYPE_CHECKING` imports to satisfy Ruff `TC003`
- Resolves `lake` via `shutil.which()` and raises `LeanRunnerError` with a clear message when missing
- Casts parsed severities to satisfy `LeanError.severity: Literal["error", "warning", "info"]` under mypy strict mode

```python
# src/erdos/core/lean_runner.py
"""Run Lean 4 and capture results."""

import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from erdos.core.models import LeanCheckResult, LeanError


class LeanRunnerError(Exception):
    """Raised when Lean operations fail."""

    pass


@dataclass
class LeanEnvironment:
    """Information about the Lean environment."""

    lean_version: str
    elan_installed: bool
    lake_installed: bool
    mathlib_available: bool
    project_path: Path


class LeanRunner:
    """
    Run Lean 4 compiler and parse results.

    Usage:
        runner = LeanRunner(Path("formal/lean"))
        result = runner.check(Path("Erdos/Problem006.lean"))
        if not result.success:
            for error in result.errors:
                print(error)
    """

    def __init__(self, project_path: Path) -> None:
        """
        Initialize Lean runner.

        Args:
            project_path: Path to Lean project (containing lakefile.lean)

        Raises:
            LeanRunnerError: If project path is invalid
        """
        if not project_path.exists():
            raise LeanRunnerError(f"Lean project not found: {project_path}")

        self._project_path = project_path
        self._lakefile = project_path / "lakefile.lean"
        self._toolchain = project_path / "lean-toolchain"

    @property
    def project_path(self) -> Path:
        """Path to the Lean project."""
        return self._project_path

    def check_environment(self) -> LeanEnvironment:
        """
        Check Lean environment status.

        Returns:
            LeanEnvironment with status information
        """
        elan = shutil.which("elan") is not None
        lake = shutil.which("lake") is not None

        lean_version = "unknown"
        if elan or shutil.which("lean"):
            try:
                result = subprocess.run(
                    ["lean", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    lean_version = result.stdout.strip().split("\n")[0]
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        mathlib = (self._project_path / "lake-packages" / "mathlib").exists() or (
            self._project_path / ".lake" / "packages" / "mathlib"
        ).exists()

        return LeanEnvironment(
            lean_version=lean_version,
            elan_installed=elan,
            lake_installed=lake,
            mathlib_available=mathlib,
            project_path=self._project_path,
        )

    def init(self, *, fetch_mathlib: bool = True) -> None:
        """
        Initialize or update the Lean project.

        Creates necessary files and fetches dependencies.

        Args:
            fetch_mathlib: If True, run `lake update` to fetch mathlib

        Raises:
            LeanRunnerError: If initialization fails
        """
        # Ensure directory exists
        self._project_path.mkdir(parents=True, exist_ok=True)
        (self._project_path / "Erdos").mkdir(exist_ok=True)

        # Create lean-toolchain if missing
        if not self._toolchain.exists():
            self._toolchain.write_text("leanprover/lean4:v4.12.0\n")

        # Create lakefile.lean if missing
        if not self._lakefile.exists():
            self._lakefile.write_text(self._default_lakefile())

        # Create Basic.lean if missing
        basic_lean = self._project_path / "Erdos" / "Basic.lean"
        if not basic_lean.exists():
            basic_lean.write_text(self._default_basic_lean())

        # Create root module if missing
        root_lean = self._project_path / "Erdos.lean"
        if not root_lean.exists():
            root_lean.write_text("-- Erdos.lean\nimport Erdos.Basic\n")

        # Fetch dependencies
        if fetch_mathlib:
            result = subprocess.run(
                ["lake", "update"],
                cwd=self._project_path,
                capture_output=True,
                text=True,
                timeout=600,  # mathlib fetch can take time
            )
            if result.returncode != 0:
                raise LeanRunnerError(
                    f"lake update failed:\n{result.stderr}\n{result.stdout}"
                )

    def check(self, file_path: Path, *, timeout: int = 120) -> LeanCheckResult:
        """
        Check a Lean file for errors.

        Args:
            file_path: Path to .lean file (relative to project or absolute)
            timeout: Maximum seconds to wait for compilation

        Returns:
            LeanCheckResult with success status and any errors
        """
        # Resolve path
        if not file_path.is_absolute():
            full_path = self._project_path / file_path
        else:
            full_path = file_path

        if not full_path.exists():
            raise FileNotFoundError(f"Lean file not found: {full_path}")

        start_time = datetime.now(timezone.utc)

        try:
            # Run lake build on the specific file
            # Convert path to module name for lake
            relative = full_path.relative_to(self._project_path)
            module_name = str(relative.with_suffix("")).replace("/", ".")

            result = subprocess.run(
                ["lake", "build", module_name],
                cwd=self._project_path,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            duration_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )

            # Parse errors from stderr
            errors = self._parse_errors(result.stderr, str(relative))
            warnings = [e for e in errors if e.severity == "warning"]
            errors = [e for e in errors if e.severity == "error"]

            # Get Lean version
            env = self.check_environment()

            return LeanCheckResult(
                file=str(relative),
                success=result.returncode == 0 and len(errors) == 0,
                errors=errors,
                warnings=warnings,
                lean_version=env.lean_version,
                duration_ms=duration_ms,
            )

        except subprocess.TimeoutExpired:
            return LeanCheckResult(
                file=str(file_path),
                success=False,
                errors=[
                    LeanError(
                        file=str(file_path),
                        line=1,
                        column=1,
                        message=f"Compilation timed out after {timeout} seconds",
                        severity="error",
                    )
                ],
            )

    def _parse_errors(self, stderr: str, file_hint: str) -> list[LeanError]:
        """
        Parse Lean compiler output into structured errors.

        Lean 4 error format:
            filename:line:column: error: message
            filename:line:column: warning: message

        Args:
            stderr: Raw stderr from lean/lake
            file_hint: Filename to use if not in error

        Returns:
            List of LeanError objects
        """
        errors = []

        # Pattern: file:line:col: severity: message
        # May span multiple lines for full message
        pattern = r"^(.+?):(\d+):(\d+):\s*(error|warning|info):\s*(.+?)(?=\n\S+:\d+:\d+:|\Z)"

        for match in re.finditer(pattern, stderr, re.MULTILINE | re.DOTALL):
            file, line, col, severity, message = match.groups()
            errors.append(
                LeanError(
                    file=file.strip(),
                    line=int(line),
                    column=int(col),
                    message=message.strip(),
                    severity=severity,
                )
            )

        # If no structured errors but stderr has content, create generic error
        if not errors and stderr.strip():
            errors.append(
                LeanError(
                    file=file_hint,
                    line=1,
                    column=1,
                    message=stderr.strip()[:500],  # Truncate long messages
                    severity="error",
                )
            )

        return errors

    def _default_lakefile(self) -> str:
        """Return default lakefile.lean content."""
        return '''import Lake
open Lake DSL

package erdos where
  leanOptions := #[
    ⟨`autoImplicit, false⟩,
    ⟨`pp.unicode.fun, true⟩
  ]

-- Pin mathlib version - update along with lean-toolchain
require mathlib from git
  "https://github.com/leanprover-community/mathlib4.git" @ "v4.12.0"

@[default_target]
lean_lib Erdos where
  globs := #[.submodules `Erdos]
'''

    def _default_basic_lean(self) -> str:
        """Return default Erdos/Basic.lean content."""
        return '''-- Erdos/Basic.lean
-- Common definitions for Erdős problem formalizations

import Mathlib.Data.Nat.Prime.Basic
import Mathlib.Data.Finset.Basic

-- Marker structure for Erdős problems
structure ErdosProblem where
  id : Nat
  title : String
  status : String
  deriving Repr
'''
```

---

## 4) Skeleton Generator

**SSOT:** `src/erdos/core/formalizer.py` + `src/erdos/templates/lean_skeleton.j2`

```python
# src/erdos/core/formalizer.py
"""Generate Lean skeletons from problem statements."""

from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape

from erdos.core.models import ProblemRecord


class FormalizerError(Exception):
    """Raised when skeleton generation fails."""

    pass


# Jinja2 environment for templates
_env = Environment(
    loader=PackageLoader("erdos", "templates"),
    autoescape=select_autoescape(),
    trim_blocks=True,
    lstrip_blocks=True,
)


def generate_skeleton(
    problem: ProblemRecord,
    project_path: Path,
    *,
    overwrite: bool = False,
) -> Path:
    """
    Generate a Lean skeleton file for a problem.

    Args:
        problem: The problem to formalize
        project_path: Path to Lean project
        overwrite: If True, overwrite existing file

    Returns:
        Path to the generated file

    Raises:
        FormalizerError: If generation fails
    """
    # Determine output path
    output_dir = project_path / "Erdos"
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"Problem{problem.id:03d}.lean"
    output_path = output_dir / filename

    if output_path.exists() and not overwrite:
        raise FormalizerError(
            f"File already exists: {output_path}. Use --force to overwrite."
        )

    # Render template
    template = _env.get_template("lean_skeleton.j2")
    content = template.render(
        problem=problem,
        problem_id_padded=f"{problem.id:03d}",
    )

    # Write file
    output_path.write_text(content)

    # Update root module to import this problem
    _update_root_module(project_path, problem.id)

    return output_path


def _update_root_module(project_path: Path, problem_id: int) -> None:
    """Add import for new problem to Erdos.lean."""
    root_lean = project_path / "Erdos.lean"
    if not root_lean.exists():
        return

    import_line = f"import Erdos.Problem{problem_id:03d}"
    content = root_lean.read_text()

    if import_line not in content:
        # Add import before the last line (or at end)
        lines = content.rstrip().split("\n")
        lines.append(import_line)
        root_lean.write_text("\n".join(lines) + "\n")
```

---

## 5) Lean Skeleton Template

```jinja2
{# src/erdos/templates/lean_skeleton.j2 #}
/-
Problem {{ problem.id }}: {{ problem.title }}

Status: {{ problem.status.value }}
{% if problem.prize > 0 %}Prize: ${{ problem.prize }}{% endif %}
{% if problem.tags %}Tags: {{ problem.tags | join(', ') }}{% endif %}

Statement:
{{ problem.statement }}
-/

import Erdos.Basic
import Mathlib.Data.Finset.Basic
import Mathlib.Data.Nat.Prime.Basic
import Mathlib.Algebra.BigOperators.Group.Finset

namespace Erdos.Problem{{ problem_id_padded }}

/-!
# Problem {{ problem.id }}: {{ problem.title }}

## Formalization Notes

This is an auto-generated skeleton. The formal statement below
may need refinement to accurately capture the problem.

## TODO
- [ ] Verify the formal statement matches the informal one
- [ ] Add necessary definitions
- [ ] Attempt proof or mark as `sorry`
-/

-- Problem metadata
def problem : ErdosProblem := {
  id := {{ problem.id }}
  title := "{{ problem.title | replace('"', '\\"') }}"
  status := "{{ problem.status.value }}"
}

-- Main theorem statement
-- TODO: Refine this formal statement
theorem problem_{{ problem.id }} : True := by
  sorry

end Erdos.Problem{{ problem_id_padded }}
```

---

## 6) CLI Commands

### `erdos lean init`

```python
@app.command()
def init(
    project_path: Annotated[
        Path | None,
        typer.Option("--path", "-p", help="Path to Lean project"),
    ] = None,
    no_mathlib: Annotated[
        bool,
        typer.Option(
            "--no-mathlib",
            help="Initialize a minimal project without mathlib (faster, offline).",
        ),
    ] = False,
) -> None:
    """
    Initialize Lean 4 project with mathlib.

    Creates lakefile.lean, lean-toolchain, and directory structure.
    Fetches mathlib dependencies (may take several minutes).
    """
    from erdos.core.lean_runner import LeanRunner

    path = project_path or Path("formal/lean")
    runner = LeanRunner(path)

    console.print(f"Initializing Lean project at {path}...")
    runner.init(fetch_mathlib=not no_mathlib)

    env = runner.check_environment()
    console.print(f"[green]✓[/green] Lean project initialized")
    console.print(f"  Lean version: {env.lean_version}")
    console.print(f"  Mathlib: {'available' if env.mathlib_available else 'not fetched'}")
```

### `erdos lean check`

```python
@app.command()
def check(
    ctx: typer.Context,
    file: Annotated[
        Path,
        typer.Argument(help="Lean file to check"),
    ],
    project_path: Annotated[
        Path | None,
        typer.Option("--path", "-p", help="Path to Lean project"),
    ] = None,
) -> None:
    """
    Check a Lean file for compilation errors.

    Example: erdos lean check Erdos/Problem006.lean
    """
    from erdos.core.lean_runner import LeanRunner

    path = project_path or Path("formal/lean")
    runner = LeanRunner(path)
    result = runner.check(file)

    json_mode = bool(ctx.obj and ctx.obj.get("json"))
    if json_mode:
        output = CLIOutput.ok(command="erdos lean check", data=result.model_dump())
        console.print_json(output.model_dump_json())
    else:
        if result.success:
            console.print(f"[green]✓[/green] {result.file} compiled successfully")
            if result.warnings:
                console.print(f"  {len(result.warnings)} warning(s)")
        else:
            console.print(f"[red]✗[/red] {result.file} failed with {len(result.errors)} error(s)")
            for error in result.errors:
                console.print(f"  {error}")

    if not result.success:
        raise typer.Exit(code=5)
```

### `erdos lean formalize`

```python
@app.command()
def formalize(
    ctx: typer.Context,
    problem_id: Annotated[
        int,
        typer.Argument(help="Problem ID to formalize", min=1),
    ],
    project_path: Annotated[
        Path | None,
        typer.Option("--path", "-p", help="Path to Lean project"),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing file"),
    ] = False,
) -> None:
    """
    Generate a Lean skeleton for a problem.

    Creates Erdos/Problem<ID>.lean with theorem stub.

    Example: erdos lean formalize 6
    """
    from erdos.core.formalizer import generate_skeleton
    from erdos.core.problem_loader import ProblemLoader

    path = project_path or Path("formal/lean")
    loader = ProblemLoader.from_default()

    problem = loader.get_by_id(problem_id)
    if problem is None:
        err_console.print(f"[red]Error:[/red] Problem {problem_id} not found")
        raise typer.Exit(code=3)

    try:
        output_file = generate_skeleton(problem, path, overwrite=force)
    except FormalizerError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

    json_mode = bool(ctx.obj and ctx.obj.get("json"))
    if json_mode:
        console.print_json(
            CLIOutput.ok(
                command="erdos lean formalize",
                data={"problem_id": problem_id, "file": str(output_file)},
            ).model_dump_json()
        )
    else:
        console.print(f"[green]✓[/green] Created {output_file}")
        console.print(f"  Run: erdos lean check {output_file}")
```

---

## 7) Verification: This Spec is Testable

### Unit Tests

```python
# tests/unit/test_lean_runner.py
"""Unit tests for LeanRunner."""

from __future__ import annotations

import pytest

from erdos.core.lean_runner import LeanRunner, LeanRunnerError

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pathlib import Path


class TestLeanRunnerInit:
    def test_raises_if_path_not_found(self, tmp_path: Path) -> None:
        """Raises if project path doesn't exist."""
        with pytest.raises(LeanRunnerError, match="not found"):
            LeanRunner(tmp_path / "nonexistent")


class TestLeanRunnerParseErrors:
    def test_parses_single_error(self) -> None:
        """Parses a single Lean error."""
        runner = LeanRunner.__new__(LeanRunner)
        stderr = "Erdos/Problem006.lean:12:5: error: unknown identifier 'Nat.prime'"

        errors = runner._parse_errors(stderr, "test.lean")

        assert len(errors) == 1
        assert errors[0].file == "Erdos/Problem006.lean"
        assert errors[0].line == 12
        assert errors[0].column == 5
        assert "unknown identifier" in errors[0].message
        assert errors[0].severity == "error"

    def test_parses_multiple_errors(self) -> None:
        """Parses multiple errors."""
        runner = LeanRunner.__new__(LeanRunner)
        stderr = """Erdos/Test.lean:10:1: error: first error
Erdos/Test.lean:20:5: warning: some warning"""

        errors = runner._parse_errors(stderr, "test.lean")

        assert len(errors) == 2
        assert errors[0].severity == "error"
        assert errors[1].severity == "warning"

    def test_handles_multiline_message(self) -> None:
        """Parses error with multiline message."""
        runner = LeanRunner.__new__(LeanRunner)
        stderr = """Erdos/Test.lean:10:1: error: type mismatch
  has type
    Nat
  but is expected to have type
    Prop"""

        errors = runner._parse_errors(stderr, "test.lean")

        assert len(errors) == 1
        assert "type mismatch" in errors[0].message

    def test_handles_empty_stderr(self) -> None:
        """Empty stderr produces no errors."""
        runner = LeanRunner.__new__(LeanRunner)
        errors = runner._parse_errors("", "test.lean")
        assert errors == []


class TestLeanRunnerCheckEnvironment:
    def test_returns_environment_info(self, tmp_path: Path) -> None:
        """check_environment returns LeanEnvironment."""
        # Create minimal project
        (tmp_path / "lakefile.lean").write_text("-- minimal", encoding="utf-8")
        runner = LeanRunner(tmp_path)

        env = runner.check_environment()

        assert env.project_path == tmp_path
        assert isinstance(env.elan_installed, bool)
        assert isinstance(env.lean_version, str)
```

### Integration Tests

```python
# tests/integration/test_lean_runner.py
"""Integration tests for Lean runner (requires Lean installed)."""

import shutil
from pathlib import Path

import pytest

from erdos.core.lean_runner import LeanRunner

lean_available = shutil.which("lean") is not None


@pytest.mark.skipif(not lean_available, reason="Lean not installed")
@pytest.mark.requires_lean
class TestLeanRunnerIntegration:
    def test_init_creates_project(self, tmp_path: Path) -> None:
        """init creates Lean project structure."""
        runner = LeanRunner(tmp_path)
        runner.init(fetch_mathlib=False)

        assert (tmp_path / "lean-toolchain").exists()
        assert (tmp_path / "lakefile.lean").exists()
        assert (tmp_path / "Erdos" / "Basic.lean").exists()

    def test_check_valid_file(self, tmp_path: Path) -> None:
        """check succeeds on valid Lean file."""
        runner = LeanRunner(tmp_path)
        runner.init(fetch_mathlib=False)

        # Create a simple valid Lean file
        test_file = tmp_path / "Erdos" / "Test.lean"
        test_file.write_text("theorem simple : 1 + 1 = 2 := rfl\n", encoding="utf-8")

        result = runner.check(test_file)

        # May fail without mathlib, but should not raise
        assert result.file == "Erdos/Test.lean"

    def test_check_invalid_file(self, tmp_path: Path) -> None:
        """check captures errors from invalid file."""
        runner = LeanRunner(tmp_path)
        runner.init(fetch_mathlib=False)

        # Create invalid Lean file
        test_file = tmp_path / "Erdos" / "Bad.lean"
        test_file.write_text("theorem bad : 1 = 2 := rfl\n", encoding="utf-8")

        result = runner.check(test_file)

        assert not result.success
        assert len(result.errors) > 0
```

### Formalization Tests

```python
# tests/unit/test_formalizer.py
"""Unit tests for skeleton generation."""

from pathlib import Path

import pytest

from erdos.core.formalizer import FormalizerError, generate_skeleton
from erdos.core.models import ProblemRecord, ProblemStatus


@pytest.fixture
def sample_problem() -> ProblemRecord:
    return ProblemRecord(
        id=6,
        title="Small primes",
        statement="Prove that there are infinitely many primes.",
        status=ProblemStatus.OPEN,
        tags=["number theory"],
    )


class TestGenerateSkeleton:
    def test_creates_lean_file(self, tmp_path: Path, sample_problem: ProblemRecord) -> None:
        """generate_skeleton creates .lean file."""
        # Create project structure
        (tmp_path / "Erdos").mkdir()
        (tmp_path / "Erdos.lean").write_text("import Erdos.Basic\n", encoding="utf-8")

        output = generate_skeleton(sample_problem, tmp_path)

        assert output.exists()
        assert output.name == "Problem006.lean"

    def test_file_contains_problem_info(self, tmp_path: Path, sample_problem: ProblemRecord) -> None:
        """Generated file contains problem information."""
        (tmp_path / "Erdos").mkdir()
        (tmp_path / "Erdos.lean").write_text("import Erdos.Basic\n", encoding="utf-8")

        output = generate_skeleton(sample_problem, tmp_path)
        content = output.read_text()

        assert "Problem 6" in content
        assert "Small primes" in content
        assert "sorry" in content  # Has placeholder proof

    def test_raises_if_file_exists(self, tmp_path: Path, sample_problem: ProblemRecord) -> None:
        """Raises if file exists and overwrite=False."""
        (tmp_path / "Erdos").mkdir()
        (tmp_path / "Erdos.lean").write_text("import Erdos.Basic\n", encoding="utf-8")
        (tmp_path / "Erdos" / "Problem006.lean").write_text("-- existing", encoding="utf-8")

        with pytest.raises(FormalizerError, match="already exists"):
            generate_skeleton(sample_problem, tmp_path, overwrite=False)

    def test_overwrites_with_force(self, tmp_path: Path, sample_problem: ProblemRecord) -> None:
        """Overwrites file when overwrite=True."""
        (tmp_path / "Erdos").mkdir()
        (tmp_path / "Erdos.lean").write_text("import Erdos.Basic\n", encoding="utf-8")
        (tmp_path / "Erdos" / "Problem006.lean").write_text("-- old content", encoding="utf-8")

        output = generate_skeleton(sample_problem, tmp_path, overwrite=True)

        assert "Small primes" in output.read_text()
```

### Acceptance Criteria

```bash
# 1. Lean project can be initialized
uv run erdos lean init --no-mathlib
ls formal/lean/
# Should show: lakefile.lean, lean-toolchain, Erdos/

# 2. Skeleton generation works
uv run erdos lean formalize 6
cat formal/lean/Erdos/Problem006.lean
# Should show generated Lean file with problem info

# 3. Lean check works (requires Lean installed)
uv run erdos lean check formal/lean/Erdos/Problem006.lean
# Should show success or structured errors

# 4. JSON output works
uv run erdos lean check formal/lean/Erdos/Problem006.lean --json
# Should output JSON with success/errors

# 5. Tests pass
uv run pytest tests/unit/test_lean_runner.py -v
uv run pytest tests/unit/test_formalizer.py -v
uv run pytest tests/integration/test_lean_runner.py -v -m requires_lean
```

---

## 8) References

- [Lean 4 Documentation](https://lean-lang.org/lean4/doc/)
- [Lake Documentation](https://github.com/leanprover/lake)
- [Mathlib4](https://github.com/leanprover-community/mathlib4)
- [Elan (Lean Version Manager)](https://github.com/leanprover/elan)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-01-16 | Initial spec |

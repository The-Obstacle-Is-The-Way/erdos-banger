"""Run Lean 4 and capture results."""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from erdos.core.models import LeanCheckResult, LeanError


if TYPE_CHECKING:
    from pathlib import Path
    from typing import Literal


logger = logging.getLogger(__name__)


class LeanRunnerError(Exception):
    """Raised when Lean operations fail."""


@dataclass
class ResolvedLeanPath:
    """Result of resolving a Lean file path to a module name."""

    full_path: Path
    relative_path: Path
    module_name: str


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
        self._cached_lean_version: str | None = None

    def _get_lean_version(self) -> str:
        """Return the Lean version, caching subprocess calls per runner instance."""
        if self._cached_lean_version is None:
            self._cached_lean_version = self.check_environment().lean_version
        return self._cached_lean_version

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
        lake_path = shutil.which("lake")
        lake = lake_path is not None

        lean_version = "unknown"
        lean_path = shutil.which("lean")
        if lean_path:
            try:
                result = subprocess.run(  # noqa: S603
                    [lean_path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                if result.returncode == 0:
                    lean_version = result.stdout.strip().split("\n")[0]
            except (subprocess.TimeoutExpired, FileNotFoundError):
                logger.debug("Failed to determine Lean version", exc_info=True)
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
        self._project_path.mkdir(parents=True, exist_ok=True)
        (self._project_path / "Erdos").mkdir(exist_ok=True)

        if not self._toolchain.exists():
            self._toolchain.write_text("leanprover/lean4:v4.12.0\n", encoding="utf-8")

        if not self._lakefile.exists():
            lakefile = (
                self._default_lakefile() if fetch_mathlib else self._minimal_lakefile()
            )
            self._lakefile.write_text(lakefile, encoding="utf-8")

        basic_lean = self._project_path / "Erdos" / "Basic.lean"
        if not basic_lean.exists():
            basic = (
                self._default_basic_lean()
                if fetch_mathlib
                else self._minimal_basic_lean()
            )
            basic_lean.write_text(basic, encoding="utf-8")

        root_lean = self._project_path / "Erdos.lean"
        if not root_lean.exists():
            root_lean.write_text(
                "-- Erdos.lean\nimport Erdos.Basic\n", encoding="utf-8"
            )

        if fetch_mathlib:
            lake_path = shutil.which("lake")
            if lake_path is None:
                raise LeanRunnerError("`lake` executable not found on PATH")

            try:
                result = subprocess.run(  # noqa: S603
                    [lake_path, "update"],
                    cwd=self._project_path,
                    capture_output=True,
                    text=True,
                    timeout=600,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise LeanRunnerError(
                    "lake update timed out after 600 seconds"
                ) from exc
            if result.returncode != 0:
                raise LeanRunnerError(
                    f"lake update failed:\n{result.stderr}\n{result.stdout}"
                )

    def _resolve_lean_path(self, file_path: Path) -> ResolvedLeanPath:
        """Resolve file path to absolute path, relative path, and module name.

        Args:
            file_path: Path to .lean file (relative to project or absolute)

        Returns:
            ResolvedLeanPath with full_path, relative_path, and module_name

        Raises:
            FileNotFoundError: If the file doesn't exist
            LeanRunnerError: If the file is not under the project path
        """
        if not file_path.is_absolute():
            full_path = self._project_path / file_path
        else:
            full_path = file_path

        if not full_path.exists():
            raise FileNotFoundError(f"Lean file not found: {full_path}")

        # Resolve symlinks for consistent behavior across environments
        resolved_full = full_path.resolve()
        resolved_project = self._project_path.resolve()

        try:
            relative = resolved_full.relative_to(resolved_project)
        except ValueError as exc:
            raise LeanRunnerError(
                f"Lean file must be under project path: {self._project_path}"
            ) from exc

        module_name = ".".join(relative.with_suffix("").parts)
        return ResolvedLeanPath(resolved_full, relative, module_name)

    def _build_check_result(
        self,
        result: subprocess.CompletedProcess[str],
        relative_path: Path,
        duration_ms: int,
    ) -> LeanCheckResult:
        """Build LeanCheckResult from subprocess output.

        Args:
            result: Completed subprocess result
            relative_path: Relative path to the Lean file
            duration_ms: Duration of the build in milliseconds

        Returns:
            LeanCheckResult with parsed errors and warnings
        """
        parsed = self._parse_errors(result.stderr)
        warnings = [e for e in parsed if e.severity == "warning"]
        errors = [e for e in parsed if e.severity == "error"]

        if result.returncode != 0 and not errors:
            raw = (result.stderr or result.stdout).strip()
            message = (
                raw[:500] if raw else f"lake build failed (exit {result.returncode})"
            )
            errors = [
                LeanError(
                    file=str(relative_path),
                    line=1,
                    column=1,
                    message=message,
                    severity="error",
                )
            ]

        return LeanCheckResult(
            file=str(relative_path),
            success=result.returncode == 0 and len(errors) == 0,
            errors=errors,
            warnings=warnings,
            lean_version=self._get_lean_version(),
            duration_ms=duration_ms,
        )

    def _timeout_result(self, relative_path: Path, timeout: int) -> LeanCheckResult:
        """Create a timeout error result.

        Args:
            relative_path: Relative path to the Lean file
            timeout: Timeout value in seconds

        Returns:
            LeanCheckResult indicating timeout failure
        """
        return LeanCheckResult(
            file=str(relative_path),
            success=False,
            errors=[
                LeanError(
                    file=str(relative_path),
                    line=1,
                    column=1,
                    message=f"Compilation timed out after {timeout} seconds",
                    severity="error",
                )
            ],
        )

    def check(self, file_path: Path, *, timeout: int = 120) -> LeanCheckResult:
        """Check a Lean file for errors.

        Args:
            file_path: Path to .lean file (relative to project or absolute)
            timeout: Maximum seconds to wait for compilation

        Returns:
            LeanCheckResult with success status and any errors

        Raises:
            FileNotFoundError: If the file doesn't exist
            LeanRunnerError: If the file is outside project path or `lake` is not found
        """
        resolved = self._resolve_lean_path(file_path)

        lake_path = shutil.which("lake")
        if lake_path is None:
            raise LeanRunnerError("`lake` executable not found on PATH")

        start_time = datetime.now(UTC)
        try:
            result = subprocess.run(  # noqa: S603
                [lake_path, "build", resolved.module_name],
                cwd=self._project_path,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            duration_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
            return self._build_check_result(result, resolved.relative_path, duration_ms)
        except subprocess.TimeoutExpired:
            return self._timeout_result(resolved.relative_path, timeout)

    def _parse_errors(self, stderr: str) -> list[LeanError]:
        """
        Parse Lean compiler output into structured errors.

        Lean 4 error format:
            filename:line:column: error: message
            filename:line:column: warning: message

        Args:
            stderr: Raw stderr from lean/lake

        Returns:
            List of LeanError objects
        """
        errors: list[LeanError] = []

        pattern = (
            r"^(.+?):(\d+):(\d+):\s*(error|warning|info):\s*(.+?)(?=\n\S+:\d+:\d+:|\Z)"
        )

        for match in re.finditer(pattern, stderr, re.MULTILINE | re.DOTALL):
            file, line, col, severity, message = match.groups()
            errors.append(
                LeanError(
                    file=file.strip(),
                    line=int(line),
                    column=int(col),
                    message=message.strip(),
                    severity=cast('Literal["error", "warning", "info"]', severity),
                )
            )

        return errors

    def _default_lakefile(self) -> str:
        """Return default lakefile.lean content."""
        return """import Lake
open Lake DSL

package erdos where
  leanOptions := #[
    ⟨`autoImplicit, false⟩,
    ⟨`pp.unicode.fun, true⟩
  ]

-- Pin mathlib version - update along with lean-toolchain
require mathlib from git
  \"https://github.com/leanprover-community/mathlib4.git\" @ \"v4.12.0\"

@[default_target]
lean_lib Erdos where
  globs := #[.submodules `Erdos]
"""

    def _minimal_lakefile(self) -> str:
        """Return a minimal lakefile.lean without mathlib (used for --no-mathlib)."""
        return """import Lake
open Lake DSL

package erdos where
  leanOptions := #[
    ⟨`autoImplicit, false⟩,
    ⟨`pp.unicode.fun, true⟩
  ]

@[default_target]
lean_lib Erdos where
  globs := #[.submodules `Erdos]
"""

    def _default_basic_lean(self) -> str:
        """Return default Erdos/Basic.lean content."""
        return """-- Erdos/Basic.lean
-- Common definitions for Erdős problem formalizations

import Mathlib.Data.Nat.Prime.Basic
import Mathlib.Data.Finset.Basic

-- Marker structure for Erdős problems
structure ErdosProblem where
  id : Nat
  title : String
  status : String
  deriving Repr
"""

    def _minimal_basic_lean(self) -> str:
        """Return minimal Erdos/Basic.lean content without Mathlib imports."""
        return """-- Erdos/Basic.lean
-- Common definitions for Erdős problem formalizations (minimal, no Mathlib).

-- Marker structure for Erdős problems
structure ErdosProblem where
  id : Nat
  title : String
  status : String
  deriving Repr
"""

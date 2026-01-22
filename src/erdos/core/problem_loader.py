"""Load and parse problems from the erdosproblems dataset."""

from __future__ import annotations

import logging
import os
from importlib.resources import as_file, files
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from pydantic import ValidationError

from erdos.core.models import ProblemRecord, ProblemStatus, ReferenceEntry


if TYPE_CHECKING:
    from collections.abc import Iterator


logger = logging.getLogger(__name__)


class ProblemLoaderError(Exception):
    """Raised when problem loading fails."""


def _validate_list_field(raw: dict[str, Any], field: str, problem_id: Any) -> list[Any]:
    """Validate and extract a list field from raw data.

    Args:
        raw: Raw problem dict
        field: Field name to extract
        problem_id: Problem ID for error messages

    Returns:
        List value (empty list if None/missing)

    Raises:
        ProblemLoaderError: If field is not a list
    """
    # Use explicit None check to avoid masking falsy non-list values like "", 0, False
    value = raw.get(field)
    if value is None:
        return []
    if isinstance(value, str):
        raise ProblemLoaderError(
            f"Problem {problem_id}: '{field}' must be a list, got string: {value!r}"
        )
    if not isinstance(value, list):
        raise ProblemLoaderError(
            f"Problem {problem_id}: '{field}' must be a list, got {type(value).__name__}"
        )
    return value


def _parse_references(raw_refs: Any) -> list[ReferenceEntry]:
    """Parse references from raw YAML data.

    Args:
        raw_refs: Raw references value from YAML

    Returns:
        List of ReferenceEntry objects

    Raises:
        ProblemLoaderError: If references format is invalid
    """
    if raw_refs is None:
        return []
    if not isinstance(raw_refs, list):
        raise ProblemLoaderError("Field 'references' must be a list")

    references: list[ReferenceEntry] = []
    for ref in raw_refs:
        if not isinstance(ref, dict):
            raise ProblemLoaderError("Each reference must be a mapping")
        key = ref.get("key")
        if not isinstance(key, str) or not key.strip():
            raise ProblemLoaderError("Each reference must include a non-empty 'key'")
        references.append(
            ReferenceEntry(
                key=key.strip(),
                citation=ref.get("citation"),
                doi=ref.get("doi"),
                arxiv_id=ref.get("arxiv_id"),
                url=ref.get("url"),
            )
        )
    return references


class ProblemLoader:
    """
    Loads problems from the erdosproblems YAML file.

    Usage:
        loader = ProblemLoader.from_default()
        problems = loader.load_all()
        problem = loader.get_by_id(6)
    """

    def __init__(self, yaml_path: Path, *, _content: str | None = None) -> None:
        """
        Initialize loader with path to problems.yaml.

        Args:
            yaml_path: Path to the problems.yaml file
            _content: Pre-loaded YAML content (internal use for package resources)

        Raises:
            ProblemLoaderError: If file doesn't exist (when _content not provided)
        """
        # If content is pre-loaded (from package resources), skip file checks
        if _content is None:
            if not yaml_path.exists():
                raise ProblemLoaderError(f"Problems file not found: {yaml_path}")
            if not yaml_path.is_file():
                raise ProblemLoaderError(f"Not a file: {yaml_path}")

        self._yaml_path = yaml_path
        self._content = _content  # Pre-loaded content (avoids as_file cleanup issue)
        self._cache: dict[int, ProblemRecord] | None = None

    @classmethod
    def _resolve_path(cls, path: Path) -> ProblemLoader | None:
        """Resolve a path (file or directory) to a ProblemLoader.

        Args:
            path: File or directory path to resolve.

        Returns:
            ProblemLoader if valid path found, None otherwise.
        """
        if path.exists() and path.is_file():
            return cls(path)
        if path.exists() and path.is_dir():
            for filename in ("problems_enriched.yaml", "problems.yaml"):
                yaml_path = path / filename
                if yaml_path.exists():
                    return cls(yaml_path)
        return None

    @classmethod
    def from_default(cls, *, data_path: Path | None = None) -> ProblemLoader:
        """
        Create loader using default data path.

        Looks for a problems YAML in these locations (in order):
        1. Explicit data_path parameter (if provided)
        2. ERDOS_DATA_PATH environment variable (file or directory)
        3. ./data/problems_enriched.yaml (relative to cwd; v1 default)
        4. Package data directory (built-in sample dataset)
        5. ./data/erdosproblems/data/problems.yaml (upstream metadata-only)

        Args:
            data_path: Explicit path to use (skips env/filesystem search).

        Returns:
            ProblemLoader instance

        Raises:
            ProblemLoaderError: If no valid path found
        """
        # 1. Explicit path from config (DIP-compliant)
        if data_path is not None:
            loader = cls._resolve_path(data_path)
            if loader is not None:
                return loader
            raise ProblemLoaderError(f"data_path not found: {data_path}")

        # 2. Environment variable (legacy fallback)
        env_path = os.environ.get("ERDOS_DATA_PATH")
        if env_path:
            loader = cls._resolve_path(Path(env_path))
            if loader is not None:
                return loader
            raise ProblemLoaderError(f"ERDOS_DATA_PATH not found: {env_path}")

        # 3. Common file paths
        return cls._find_default_paths()

    @classmethod
    def _find_default_paths(cls) -> ProblemLoader:
        """Search default filesystem locations for problems YAML.

        Returns:
            ProblemLoader instance

        Raises:
            ProblemLoaderError: If no valid path found
        """
        enriched_path = Path("data/problems_enriched.yaml")
        if enriched_path.exists():
            return cls(enriched_path)

        try:
            pkg_files = files("erdos")
            pkg_data = pkg_files.joinpath("data", "problems_enriched.yaml")
            with as_file(pkg_data) as real_path:
                if real_path.exists():
                    content = real_path.read_text(encoding="utf-8")
                    return cls(real_path, _content=content)
        except (ImportError, TypeError, AttributeError, FileNotFoundError):
            logger.debug("Package data loading skipped", exc_info=True)

        relative_path = Path("data/erdosproblems/data/problems.yaml")
        if relative_path.exists():
            return cls(relative_path)

        raise ProblemLoaderError(
            "Could not find problems YAML. "
            "Set ERDOS_DATA_PATH or create data/problems_enriched.yaml."
        )

    @property
    def yaml_path(self) -> Path:
        """Path to the problems.yaml file."""
        return self._yaml_path

    def _load_raw(self) -> list[dict[str, Any]]:
        """Load raw YAML data."""
        try:
            # Use pre-loaded content if available (from package resources)
            if self._content is not None:
                data = yaml.safe_load(self._content)
            else:
                with self._yaml_path.open(encoding="utf-8") as f:
                    data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ProblemLoaderError(f"Failed to parse YAML: {e}") from e

        if not isinstance(data, list):
            raise ProblemLoaderError(
                f"Expected list of problems, got {type(data).__name__}"
            )

        raw: list[dict[str, Any]] = []
        for item in data:
            if not isinstance(item, dict):
                raise ProblemLoaderError(
                    f"Expected each problem to be a mapping, got {type(item).__name__}"
                )
            raw.append(item)
        return raw

    def _validate_required_fields(self, raw: dict[str, Any]) -> None:
        """Validate that required fields are present.

        Raises:
            ProblemLoaderError: If required fields are missing
        """
        if "id" not in raw:
            if "number" in raw:
                raise ProblemLoaderError(
                    "Unsupported upstream teorth/erdosproblems format (metadata-only). "
                    "v1 requires enriched problems with id/title/statement. "
                    "Create data/problems_enriched.yaml (Spec 005) or point ERDOS_DATA_PATH at an enriched problems_enriched.yaml (or problems.yaml)."
                )
            raise ProblemLoaderError("Missing required field 'id' in problem entry")
        if "title" not in raw or "statement" not in raw:
            raise ProblemLoaderError(
                "Missing required enriched fields 'title'/'statement'. "
                "Create data/problems_enriched.yaml (Spec 005) or point ERDOS_DATA_PATH at an enriched problems_enriched.yaml (or problems.yaml)."
            )

    def _parse_problem(self, raw: dict[str, Any]) -> ProblemRecord:
        """Parse a single problem from raw YAML dict."""
        self._validate_required_fields(raw)

        problem_id = raw.get("id")
        raw_tags = _validate_list_field(raw, "tags", problem_id)
        raw_oeis = _validate_list_field(raw, "oeis_ids", problem_id)
        references = _parse_references(raw.get("references"))

        # Validate formalized field type (bool("false") == True is a bug)
        raw_formalized = raw.get("formalized")
        if raw_formalized is not None and not isinstance(raw_formalized, bool):
            raise ProblemLoaderError(
                f"Problem {problem_id}: 'formalized' must be a bool, got {type(raw_formalized).__name__}"
            )

        return ProblemRecord(
            id=int(raw["id"]),
            title=str(raw["title"]),
            statement=str(raw["statement"]),
            status=ProblemStatus.from_string(str(raw.get("status", "open"))),
            prize=int(raw.get("prize", 0) or 0),
            tags=[str(t) for t in raw_tags],
            references=references,
            oeis_ids=[str(o) for o in raw_oeis],
            notes=raw.get("notes"),
            formalized=raw_formalized if isinstance(raw_formalized, bool) else False,
        )

    def load_all(self, *, use_cache: bool = True) -> list[ProblemRecord]:
        """
        Load all problems from the YAML file.

        Args:
            use_cache: If True, return cached results on subsequent calls

        Returns:
            List of all ProblemRecord objects

        Raises:
            ProblemLoaderError: If parsing fails
        """
        if use_cache and self._cache is not None:
            return list(self._cache.values())

        raw_problems = self._load_raw()
        problems: dict[int, ProblemRecord] = {}
        errors: list[str] = []

        for i, raw in enumerate(raw_problems):
            try:
                problem = self._parse_problem(raw)
                if problem.id in problems:
                    errors.append(
                        f"Problem at index {i}: Duplicate ID {problem.id} "
                        f"(first seen: '{problems[problem.id].title}')"
                    )
                    continue
                problems[problem.id] = problem
            except (
                ProblemLoaderError,
                KeyError,
                TypeError,
                ValueError,
                ValidationError,
            ) as e:
                errors.append(f"Problem at index {i}: {e}")

        if errors:
            raise ProblemLoaderError(
                f"Failed to parse {len(errors)} problems:\n" + "\n".join(errors[:5])
            )

        self._cache = problems
        return list(problems.values())

    def iter_problems(self) -> Iterator[ProblemRecord]:
        """
        Iterate over problems lazily.

        Yields:
            ProblemRecord objects one at a time
        """
        raw_problems = self._load_raw()
        seen: dict[int, str] = {}
        for i, raw in enumerate(raw_problems):
            try:
                problem = self._parse_problem(raw)
            except (
                ProblemLoaderError,
                KeyError,
                TypeError,
                ValueError,
                ValidationError,
            ) as e:
                raise ProblemLoaderError(f"Problem at index {i}: {e}") from e
            if problem.id in seen:
                raise ProblemLoaderError(
                    f"Problem at index {i}: Duplicate ID {problem.id} "
                    f"(first seen: '{seen[problem.id]}')"
                )
            seen[problem.id] = problem.title
            yield problem

    def get_by_id(self, problem_id: int) -> ProblemRecord | None:
        """
        Get a specific problem by ID.

        Args:
            problem_id: The problem ID to look up

        Returns:
            ProblemRecord if found, None otherwise
        """
        if self._cache is None:
            self.load_all()

        if self._cache is None:
            return None
        return self._cache.get(problem_id)

    def filter(
        self,
        *,
        status: ProblemStatus | None = None,
        prize_min: int | None = None,
        prize_max: int | None = None,
        tags: list[str] | None = None,
        formalized: bool | None = None,
    ) -> list[ProblemRecord]:
        """
        Filter problems by criteria.

        Args:
            status: Filter by problem status
            prize_min: Minimum prize amount
            prize_max: Maximum prize amount
            tags: Filter by tags (matches if problem has ANY of these tags)
            formalized: Filter by formalization status

        Returns:
            List of matching ProblemRecord objects
        """
        problems = self.load_all()
        results: list[ProblemRecord] = []

        for problem in problems:
            if status is not None and problem.status != status:
                continue

            if prize_min is not None and problem.prize < prize_min:
                continue
            if prize_max is not None and problem.prize > prize_max:
                continue

            if tags is not None and tags:  # Treat empty list as "no filter"
                tag_set = {t.lower() for t in tags}
                problem_tags = {t.lower() for t in problem.tags}
                if not tag_set.intersection(problem_tags):
                    continue

            if formalized is not None and problem.formalized != formalized:
                continue

            results.append(problem)

        return results

    def count(self) -> int:
        """Return total number of problems."""
        return len(self.load_all())

    def clear_cache(self) -> None:
        """Clear the internal cache."""
        self._cache = None

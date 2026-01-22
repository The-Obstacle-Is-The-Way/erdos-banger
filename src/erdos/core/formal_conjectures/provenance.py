"""ProvenanceFile model and YAML IO."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path  # noqa: TC003 - Used at runtime

import yaml


@dataclass
class ProvenanceEntry:
    """Record of an imported formalization."""

    problem_id: int
    source: str
    url: str
    imported_at: datetime
    sha256: str
    remote_etag: str | None = None


@dataclass
class ProvenanceFile:
    """Provenance tracking file model."""

    schema_version: int = 1
    imports: list[ProvenanceEntry] = field(default_factory=list)

    def get_by_problem_id(self, problem_id: int) -> ProvenanceEntry | None:
        """Find provenance entry by problem ID."""
        for entry in self.imports:
            if entry.problem_id == problem_id:
                return entry
        return None

    def upsert(self, entry: ProvenanceEntry) -> None:
        """Insert or update provenance entry."""
        for i, existing in enumerate(self.imports):
            if existing.problem_id == entry.problem_id:
                self.imports[i] = entry
                return
        self.imports.append(entry)


def save_provenance(prov_path: Path, prov: ProvenanceFile) -> None:
    """Save provenance file to disk.

    Args:
        prov_path: Path to provenance file
        prov: ProvenanceFile to save
    """
    prov_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "schema_version": prov.schema_version,
        "imports": [
            {
                "problem_id": e.problem_id,
                "source": e.source,
                "url": e.url,
                "imported_at": e.imported_at.isoformat(),
                "sha256": e.sha256,
                **({"remote_etag": e.remote_etag} if e.remote_etag else {}),
            }
            for e in prov.imports
        ],
    }

    with prov_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)


def load_provenance(prov_path: Path) -> ProvenanceFile:
    """Load provenance file from disk.

    Args:
        prov_path: Path to provenance file

    Returns:
        ProvenanceFile (empty if file doesn't exist)
    """
    if not prov_path.exists():
        return ProvenanceFile()

    with prov_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        return ProvenanceFile()
    if not isinstance(data, dict):
        raise ValueError(
            f"Invalid provenance file format at {prov_path} (expected a mapping)"
        )

    imports = []
    for item in data.get("imports", []):
        imports.append(
            ProvenanceEntry(
                problem_id=item["problem_id"],
                source=item["source"],
                url=item["url"],
                imported_at=datetime.fromisoformat(item["imported_at"]),
                sha256=item["sha256"],
                remote_etag=item.get("remote_etag"),
            )
        )

    return ProvenanceFile(
        schema_version=data.get("schema_version", 1),
        imports=imports,
    )

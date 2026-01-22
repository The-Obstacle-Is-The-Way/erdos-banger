"""Local file inspection: sorry/admit detection, sha256 hashing."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path  # noqa: TC003 - Used at runtime

from erdos.core.formal_conjectures.config import FormalConjecturesError


def has_sorry(content: str) -> bool:
    """Check if Lean content contains sorry or admit.

    Args:
        content: Lean file content

    Returns:
        True if sorry/admit found outside comments
    """
    # Remove block comments
    content_no_block = re.sub(r"/\-.*?\-/", "", content, flags=re.DOTALL)

    # Process line by line, removing single-line comments
    for line in content_no_block.split("\n"):
        # Remove everything after --
        code_part = line.split("--")[0]
        # Check for sorry/admit at word boundaries
        if re.search(r"\bsorry\b", code_part) or re.search(r"\badmit\b", code_part):
            return True

    return False


def compute_file_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of file content.

    Args:
        file_path: Path to file

    Returns:
        Hex-encoded SHA-256 hash

    Raises:
        FormalConjecturesError: If file not found
    """
    if not file_path.exists():
        raise FormalConjecturesError(
            f"File not found: {file_path}",
            error_type="NotFound",
        )

    content = file_path.read_bytes()
    return hashlib.sha256(content).hexdigest()


@dataclass
class LocalFormalizationInfo:
    """Information about local formalization file."""

    path: Path
    exists: bool
    has_sorry: bool | None = None
    sha256: str | None = None
    last_modified: datetime | None = None

    @classmethod
    def from_file(cls, file_path: Path) -> LocalFormalizationInfo:
        """Create info from file path.

        Args:
            file_path: Path to local Lean file

        Returns:
            LocalFormalizationInfo with file details
        """
        if not file_path.exists():
            return cls(path=file_path, exists=False)

        # Read bytes once, decode for content
        content_bytes = file_path.read_bytes()
        content = content_bytes.decode("utf-8")
        stat = file_path.stat()

        return cls(
            path=file_path,
            exists=True,
            has_sorry=has_sorry(content),
            sha256=hashlib.sha256(content_bytes).hexdigest(),
            last_modified=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
        )

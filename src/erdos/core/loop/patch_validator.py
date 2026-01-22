"""Patch validation for the loop command.

Validates LLM-generated SEARCH/REPLACE patches before application.
Per spec-012-design.md D6: Strict Validation Pipeline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pathlib import Path

    from erdos.core.loop.config import LoopConfig


# Regex for parsing SEARCH/REPLACE blocks
# Matches:
#   <<<<<<< SEARCH
#   [search content]
#   =======
#   [replace content - may be empty]
#   >>>>>>> REPLACE
SEARCH_REPLACE_PATTERN = re.compile(
    r"<<<<<<< SEARCH\n(?P<search>.*?)\n=======\n(?P<replace>.*?)>>>>>>> REPLACE",
    re.DOTALL,
)

# Regex for matching Lean keywords as whole words
# Uses word boundaries to avoid matching "sorrytown" for "sorry"
KEYWORD_PATTERN = re.compile(r"\b(sorry|admit)\b")


class MatchStatus(Enum):
    """Status of a match attempt."""

    EXACT = auto()
    NEWLINE_NORMALIZED = auto()
    AMBIGUOUS = auto()
    NOT_FOUND = auto()


class PatchStatus(Enum):
    """Status of a patch validation."""

    OK = auto()
    REJECTED = auto()
    NO_FIX = auto()


@dataclass
class MatchResult:
    """Result of finding search text in file content."""

    status: MatchStatus
    location: int | None = None
    count: int = 0

    @classmethod
    def exact(cls, location: int) -> MatchResult:
        return cls(status=MatchStatus.EXACT, location=location, count=1)

    @classmethod
    def newline_normalized(cls, location: int = 0) -> MatchResult:
        return cls(status=MatchStatus.NEWLINE_NORMALIZED, location=location, count=1)

    @classmethod
    def ambiguous(cls, count: int) -> MatchResult:
        return cls(status=MatchStatus.AMBIGUOUS, count=count)

    @classmethod
    def not_found(cls) -> MatchResult:
        return cls(status=MatchStatus.NOT_FOUND)


@dataclass
class PatchResult:
    """Result of patch validation."""

    status: PatchStatus
    search_text: str | None = None
    replace_text: str | None = None
    match_location: int | None = None
    rejection_reason: str = ""

    @classmethod
    def ok(
        cls, *, search_text: str, replace_text: str, match_location: int
    ) -> PatchResult:
        return cls(
            status=PatchStatus.OK,
            search_text=search_text,
            replace_text=replace_text,
            match_location=match_location,
        )

    @classmethod
    def reject(cls, reason: str) -> PatchResult:
        return cls(status=PatchStatus.REJECTED, rejection_reason=reason)

    @classmethod
    def no_fix(cls) -> PatchResult:
        return cls(status=PatchStatus.NO_FIX)


def parse_search_replace(response: str) -> tuple[str, str] | None:
    """Parse a SEARCH/REPLACE block from LLM response.

    Args:
        response: Raw LLM output

    Returns:
        Tuple of (search_text, replace_text) if found, None otherwise
    """
    match = SEARCH_REPLACE_PATTERN.search(response)
    if not match:
        return None
    search = match.group("search")
    replace = match.group("replace")
    # Strip trailing newline from replace (regex captures up to >>>>>>> REPLACE)
    if replace.endswith("\n"):
        replace = replace[:-1]
    return search, replace


def find_all_occurrences(needle: str, haystack: str) -> list[int]:
    """Find all occurrences of needle in haystack.

    Args:
        needle: Text to find
        haystack: Text to search in

    Returns:
        List of starting indices where needle was found
    """
    locations = []
    start = 0
    while True:
        idx = haystack.find(needle, start)
        if idx == -1:
            break
        locations.append(idx)
        start = idx + 1
    return locations


def find_match(search_text: str, file_content: str) -> MatchResult:
    """Find search_text in file_content with fallback strategies.

    Per spec-012-design.md D7: Strict Matching Only (v1.2)

    Fallback chain:
    1. Exact match
    2. Newline-normalized match (\\r\\n -> \\n)
    3. Reject (no fuzzy matching)

    Args:
        search_text: Text to find
        file_content: Content of the target file

    Returns:
        MatchResult with status and location
    """
    # Pass 1: Exact match
    if search_text in file_content:
        locations = find_all_occurrences(search_text, file_content)
        if len(locations) == 1:
            return MatchResult.exact(locations[0])
        return MatchResult.ambiguous(len(locations))

    # Pass 2: Newline-normalized match (\r\n -> \n)
    normalized_search = search_text.replace("\r\n", "\n")
    normalized_file = file_content.replace("\r\n", "\n")
    if normalized_search in normalized_file:
        locations = find_all_occurrences(normalized_search, normalized_file)
        if len(locations) == 1:
            return MatchResult.newline_normalized(locations[0])
        return MatchResult.ambiguous(len(locations))

    return MatchResult.not_found()


def count_keyword(text: str, keyword: str) -> int:
    """Count occurrences of a keyword as a whole word.

    Uses word boundaries to avoid matching partial words
    (e.g., "sorry" doesn't match "sorrytown").

    Args:
        text: Text to search
        keyword: Keyword to count ("sorry" or "admit")

    Returns:
        Number of occurrences
    """
    pattern = re.compile(rf"\b{re.escape(keyword)}\b")
    return len(pattern.findall(text))


def is_bracket_balanced(text: str) -> bool:
    """Check if brackets are balanced in the text.

    Checks parentheses (), square brackets [], and curly braces {}.

    Args:
        text: Text to check

    Returns:
        True if all brackets are balanced
    """
    stack: list[str] = []
    pairs = {"(": ")", "[": "]", "{": "}"}

    for char in text:
        if char in pairs:
            stack.append(char)
        elif char in pairs.values():
            if not stack:
                return False
            expected_open = next(k for k, v in pairs.items() if v == char)
            if stack[-1] != expected_open:
                return False
            stack.pop()

    return len(stack) == 0


def _is_under_erdos_dir(file_path: Path) -> bool:
    """Check if file is under a formal/lean/Erdos/ directory structure.

    Args:
        file_path: Path to check

    Returns:
        True if path contains the expected directory structure
    """
    parts = file_path.resolve().parts
    # Look for "Erdos" directory preceded by "lean" (could have "formal" before)
    for i, part in enumerate(parts):
        if part == "Erdos" and i > 0 and parts[i - 1] == "lean":
            return True
    return False


def validate_patch(  # noqa: PLR0911
    response: str, target_file: Path, config: LoopConfig
) -> PatchResult:
    """Validate LLM response and return applicable patch or rejection.

    Per spec-012-design.md D6: Strict Validation Pipeline.

    Args:
        response: Raw LLM output
        target_file: Path to the Lean file being edited
        config: Loop configuration with limits

    Returns:
        PatchResult with status and details
    """
    # 1. Check for explicit "no fix" response
    if response.strip() == "NO_FIX_POSSIBLE":
        return PatchResult.no_fix()

    # 2. Parse SEARCH/REPLACE block
    parsed = parse_search_replace(response)
    if parsed is None:
        return PatchResult.reject("No valid SEARCH/REPLACE block found")

    search_text, replace_text = parsed

    # 3. Size validation (bytes)
    if len(replace_text.encode("utf-8")) > config.max_patch_bytes:
        return PatchResult.reject(f"Patch exceeds {config.max_patch_bytes} bytes")

    # 4. Size validation (lines)
    # Use splitlines() to count actual lines (count("\n") gives separators, not lines)
    line_count = len(replace_text.splitlines()) if replace_text else 0
    if line_count > config.max_patch_lines:
        return PatchResult.reject(f"Patch exceeds {config.max_patch_lines} lines")

    # 5. Path validation (security)
    if not _is_under_erdos_dir(target_file):
        return PatchResult.reject("Target file outside formal/lean/Erdos/")

    # 6. Find match in target file
    file_content = target_file.read_text(encoding="utf-8")
    match_result = find_match(search_text, file_content)

    if match_result.status == MatchStatus.NOT_FOUND:
        return PatchResult.reject("SEARCH block not found in file")

    if match_result.status == MatchStatus.AMBIGUOUS:
        return PatchResult.reject(
            f"SEARCH block matches multiple locations ({match_result.count})"
        )

    # 7. Check for placeholder injection (sorry/admit)
    search_sorries = count_keyword(search_text, "sorry")
    replace_sorries = count_keyword(replace_text, "sorry")
    search_admits = count_keyword(search_text, "admit")
    replace_admits = count_keyword(replace_text, "admit")

    if replace_admits > search_admits:
        return PatchResult.reject("Patch adds admit - rejected")

    sorry_delta = replace_sorries - search_sorries
    if sorry_delta > config.allow_sorry_increase:
        return PatchResult.reject(
            f"Patch adds {sorry_delta} sorry - rejected "
            f"(use --allow-sorry-increase to override)"
        )

    # 8. Syntax sanity check (bracket balance)
    if not is_bracket_balanced(replace_text):
        return PatchResult.reject("Replacement has unbalanced brackets")

    return PatchResult.ok(
        search_text=search_text,
        replace_text=replace_text,
        match_location=match_result.location or 0,
    )

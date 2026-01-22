"""Backward-compatible shim for patch_validator.

This module has been moved to erdos.core.loop.patch_validator.
This shim exists for backward compatibility and will be removed in a future version.
"""

from erdos.core.loop.patch_validator import (
    KEYWORD_PATTERN,
    SEARCH_REPLACE_PATTERN,
    MatchResult,
    MatchStatus,
    PatchResult,
    PatchStatus,
    _is_under_erdos_dir,
    count_keyword,
    find_all_occurrences,
    find_match,
    is_bracket_balanced,
    parse_search_replace,
    validate_patch,
)


__all__ = [
    "KEYWORD_PATTERN",
    "SEARCH_REPLACE_PATTERN",
    "MatchResult",
    "MatchStatus",
    "PatchResult",
    "PatchStatus",
    "_is_under_erdos_dir",
    "count_keyword",
    "find_all_occurrences",
    "find_match",
    "is_bracket_balanced",
    "parse_search_replace",
    "validate_patch",
]

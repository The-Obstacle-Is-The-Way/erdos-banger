"""Tests for patch validation."""

from pathlib import Path

import pytest

from erdos.core.loop.config import LoopConfig
from erdos.core.loop.patch_validator import (
    MatchStatus,
    PatchResult,
    PatchStatus,
    count_keyword,
    find_match,
    is_bracket_balanced,
    parse_search_replace,
    validate_patch,
)


class TestParseSearchReplace:
    """Test SEARCH/REPLACE block parsing."""

    def test_parse_valid_block(self) -> None:
        response = """Some preamble text

<<<<<<< SEARCH
def foo():
    pass
=======
def foo():
    return 42
>>>>>>> REPLACE

Some epilogue"""
        result = parse_search_replace(response)
        assert result is not None
        assert result[0] == "def foo():\n    pass"
        assert result[1] == "def foo():\n    return 42"

    def test_parse_empty_replace(self) -> None:
        response = """<<<<<<< SEARCH
old code
=======
>>>>>>> REPLACE"""
        result = parse_search_replace(response)
        assert result is not None
        assert result[0] == "old code"
        assert result[1] == ""

    def test_parse_no_block(self) -> None:
        response = "Just some text without any blocks"
        result = parse_search_replace(response)
        assert result is None

    def test_parse_incomplete_block(self) -> None:
        response = """<<<<<<< SEARCH
old code
=======
new code"""
        result = parse_search_replace(response)
        assert result is None

    def test_parse_preserves_whitespace(self) -> None:
        response = """<<<<<<< SEARCH
  indented
    more indent
=======
  replaced
    also indented
>>>>>>> REPLACE"""
        result = parse_search_replace(response)
        assert result is not None
        assert result[0] == "  indented\n    more indent"
        assert result[1] == "  replaced\n    also indented"


class TestFindMatch:
    """Test finding search text in file content."""

    def test_exact_match_single_occurrence(self) -> None:
        file_content = "line1\ntarget line\nline3"
        result = find_match("target line", file_content)
        assert result.status == MatchStatus.EXACT
        assert result.location == 6  # Index of 'target line'

    def test_exact_match_at_start(self) -> None:
        file_content = "target line\nline2"
        result = find_match("target line", file_content)
        assert result.status == MatchStatus.EXACT
        assert result.location == 0

    def test_exact_match_at_end(self) -> None:
        file_content = "line1\ntarget line"
        result = find_match("target line", file_content)
        assert result.status == MatchStatus.EXACT

    def test_multiple_occurrences_ambiguous(self) -> None:
        file_content = "target\nother\ntarget"
        result = find_match("target", file_content)
        assert result.status == MatchStatus.AMBIGUOUS
        assert result.count == 2

    def test_not_found(self) -> None:
        file_content = "line1\nline2\nline3"
        result = find_match("not here", file_content)
        assert result.status == MatchStatus.NOT_FOUND

    def test_newline_normalized_match(self) -> None:
        # File has Unix newlines, search has Windows newlines
        file_content = "line1\nline2\nline3"
        search_text = "line1\r\nline2"
        result = find_match(search_text, file_content)
        assert result.status == MatchStatus.NEWLINE_NORMALIZED


class TestCountKeyword:
    """Test sorry/admit counting."""

    def test_count_sorry_basic(self) -> None:
        text = "theorem foo : True := sorry"
        assert count_keyword(text, "sorry") == 1

    def test_count_sorry_multiple(self) -> None:
        text = """
theorem foo : True := sorry
lemma bar : False := sorry
example : Nat := sorry
"""
        assert count_keyword(text, "sorry") == 3

    def test_count_sorry_none(self) -> None:
        text = "theorem foo : True := by trivial"
        assert count_keyword(text, "sorry") == 0

    def test_count_admit(self) -> None:
        text = "theorem foo : True := by admit"
        assert count_keyword(text, "admit") == 1

    def test_count_ignores_partial_match(self) -> None:
        # "sorrytown" should not count as sorry
        text = "-- sorrytown is not a placeholder"
        assert count_keyword(text, "sorry") == 0

    def test_count_in_comment(self) -> None:
        # sorry in comments still counts (conservative approach)
        text = "-- TODO: sorry\ntheorem foo : True := sorry"
        assert count_keyword(text, "sorry") == 2


class TestIsBracketBalanced:
    """Test bracket balance checking."""

    def test_balanced_empty(self) -> None:
        assert is_bracket_balanced("") is True

    def test_balanced_no_brackets(self) -> None:
        assert is_bracket_balanced("just text") is True

    def test_balanced_parens(self) -> None:
        assert is_bracket_balanced("(a + b)") is True

    def test_balanced_nested(self) -> None:
        assert is_bracket_balanced("((a) + (b))") is True

    def test_balanced_mixed(self) -> None:
        assert is_bracket_balanced("fun (x : Nat) => { a := [1, 2] }") is True

    def test_unbalanced_open_paren(self) -> None:
        assert is_bracket_balanced("(a + b") is False

    def test_unbalanced_close_paren(self) -> None:
        assert is_bracket_balanced("a + b)") is False

    def test_unbalanced_mixed(self) -> None:
        assert is_bracket_balanced("(a + [b)") is False

    def test_balanced_lean_code(self) -> None:
        code = """
theorem problem_6 : True := by
  have h : Nat := 0
  trivial
"""
        assert is_bracket_balanced(code) is True


class TestPatchResult:
    """Test PatchResult construction."""

    def test_ok_result(self) -> None:
        result = PatchResult.ok(
            search_text="old",
            replace_text="new",
            match_location=10,
        )
        assert result.status == PatchStatus.OK
        assert result.search_text == "old"
        assert result.replace_text == "new"
        assert result.match_location == 10

    def test_reject_result(self) -> None:
        result = PatchResult.reject("Patch too large")
        assert result.status == PatchStatus.REJECTED
        assert result.rejection_reason == "Patch too large"

    def test_no_fix_result(self) -> None:
        result = PatchResult.no_fix()
        assert result.status == PatchStatus.NO_FIX


class TestValidatePatch:
    """Test full patch validation pipeline."""

    @pytest.fixture
    def config(self) -> LoopConfig:
        return LoopConfig()

    @pytest.fixture
    def temp_lean_file(self, tmp_path: Path) -> Path:
        """Create a temporary Lean file."""
        formal_dir = tmp_path / "formal" / "lean" / "Erdos"
        formal_dir.mkdir(parents=True)
        lean_file = formal_dir / "Problem001.lean"
        lean_file.write_text(
            """theorem problem_1 : True := by
  sorry
""",
            encoding="utf-8",
        )
        return lean_file

    def test_no_fix_possible_response(
        self, config: LoopConfig, temp_lean_file: Path
    ) -> None:
        response = "NO_FIX_POSSIBLE"
        result = validate_patch(response, temp_lean_file, config)
        assert result.status == PatchStatus.NO_FIX

    def test_no_fix_possible_with_whitespace(
        self, config: LoopConfig, temp_lean_file: Path
    ) -> None:
        response = "  NO_FIX_POSSIBLE  \n"
        result = validate_patch(response, temp_lean_file, config)
        assert result.status == PatchStatus.NO_FIX

    def test_no_search_replace_block(
        self, config: LoopConfig, temp_lean_file: Path
    ) -> None:
        response = "Here's a suggestion but no valid block"
        result = validate_patch(response, temp_lean_file, config)
        assert result.status == PatchStatus.REJECTED
        assert "No valid SEARCH/REPLACE block found" in result.rejection_reason

    def test_patch_exceeds_bytes(
        self, config: LoopConfig, temp_lean_file: Path
    ) -> None:
        config_small = LoopConfig(max_patch_bytes=10)
        response = """<<<<<<< SEARCH
sorry
=======
this is a really long replacement that exceeds the limit
>>>>>>> REPLACE"""
        result = validate_patch(response, temp_lean_file, config_small)
        assert result.status == PatchStatus.REJECTED
        assert "exceeds" in result.rejection_reason
        assert "bytes" in result.rejection_reason

    def test_patch_exceeds_lines(
        self, config: LoopConfig, temp_lean_file: Path
    ) -> None:
        config_small = LoopConfig(max_patch_lines=2)
        response = """<<<<<<< SEARCH
sorry
=======
line1
line2
line3
line4
>>>>>>> REPLACE"""
        result = validate_patch(response, temp_lean_file, config_small)
        assert result.status == PatchStatus.REJECTED
        assert "exceeds" in result.rejection_reason
        assert "lines" in result.rejection_reason

    def test_search_not_found(self, config: LoopConfig, temp_lean_file: Path) -> None:
        response = """<<<<<<< SEARCH
nonexistent code
=======
replacement
>>>>>>> REPLACE"""
        result = validate_patch(response, temp_lean_file, config)
        assert result.status == PatchStatus.REJECTED
        assert "not found" in result.rejection_reason.lower()

    def test_search_ambiguous(self, tmp_path: Path) -> None:
        # Create file with duplicate content
        formal_dir = tmp_path / "formal" / "lean" / "Erdos"
        formal_dir.mkdir(parents=True)
        lean_file = formal_dir / "Problem002.lean"
        lean_file.write_text("sorry\nsorry\n", encoding="utf-8")

        response = """<<<<<<< SEARCH
sorry
=======
trivial
>>>>>>> REPLACE"""
        result = validate_patch(response, lean_file, LoopConfig())
        assert result.status == PatchStatus.REJECTED
        assert "multiple" in result.rejection_reason.lower()

    def test_adds_admit_rejected(
        self, config: LoopConfig, temp_lean_file: Path
    ) -> None:
        response = """<<<<<<< SEARCH
sorry
=======
admit
>>>>>>> REPLACE"""
        result = validate_patch(response, temp_lean_file, config)
        assert result.status == PatchStatus.REJECTED
        assert "admit" in result.rejection_reason.lower()

    def test_adds_sorry_rejected_by_default(
        self, config: LoopConfig, temp_lean_file: Path
    ) -> None:
        response = """<<<<<<< SEARCH
theorem problem_1 : True := by
  sorry
=======
theorem problem_1 : True := by
  sorry
  sorry
>>>>>>> REPLACE"""
        result = validate_patch(response, temp_lean_file, config)
        assert result.status == PatchStatus.REJECTED
        assert "sorry" in result.rejection_reason.lower()

    def test_adds_sorry_allowed_with_flag(self, temp_lean_file: Path) -> None:
        config = LoopConfig(allow_sorry_increase=1)
        response = """<<<<<<< SEARCH
theorem problem_1 : True := by
  sorry
=======
theorem problem_1 : True := by
  sorry
  sorry
>>>>>>> REPLACE"""
        result = validate_patch(response, temp_lean_file, config)
        # It adds 1 sorry, which is within the allowed limit
        assert result.status == PatchStatus.OK

    def test_removes_sorry_allowed(
        self, config: LoopConfig, temp_lean_file: Path
    ) -> None:
        response = """<<<<<<< SEARCH
theorem problem_1 : True := by
  sorry
=======
theorem problem_1 : True := by
  trivial
>>>>>>> REPLACE"""
        result = validate_patch(response, temp_lean_file, config)
        assert result.status == PatchStatus.OK
        assert result.search_text is not None
        assert result.replace_text is not None

    def test_unbalanced_brackets_rejected(
        self, config: LoopConfig, temp_lean_file: Path
    ) -> None:
        response = """<<<<<<< SEARCH
sorry
=======
(unbalanced
>>>>>>> REPLACE"""
        result = validate_patch(response, temp_lean_file, config)
        assert result.status == PatchStatus.REJECTED
        assert "bracket" in result.rejection_reason.lower()

    def test_valid_patch_ok(self, config: LoopConfig, temp_lean_file: Path) -> None:
        response = """<<<<<<< SEARCH
  sorry
=======
  trivial
>>>>>>> REPLACE"""
        result = validate_patch(response, temp_lean_file, config)
        assert result.status == PatchStatus.OK
        assert result.search_text == "  sorry"
        assert result.replace_text == "  trivial"
        assert result.match_location is not None

    def test_file_outside_erdos_rejected(self, tmp_path: Path) -> None:
        # Create file outside the expected directory
        other_file = tmp_path / "other.lean"
        other_file.write_text("sorry\n", encoding="utf-8")

        response = """<<<<<<< SEARCH
sorry
=======
trivial
>>>>>>> REPLACE"""
        result = validate_patch(response, other_file, LoopConfig())
        assert result.status == PatchStatus.REJECTED
        assert "outside" in result.rejection_reason.lower()

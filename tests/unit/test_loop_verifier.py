"""Tests for loop verification."""

from erdos.core.loop.verifier import (
    LoopExitCondition,
    LoopVerification,
    count_admits,
    count_sorries,
)


class TestCountSorries:
    """Test sorry counting."""

    def test_no_sorries(self) -> None:
        text = """
theorem foo : True := by
  trivial
"""
        assert count_sorries(text) == 0

    def test_single_sorry(self) -> None:
        text = "theorem foo : True := sorry"
        assert count_sorries(text) == 1

    def test_multiple_sorries(self) -> None:
        text = """
theorem foo : True := sorry
lemma bar : False := sorry
example : Nat := sorry
"""
        assert count_sorries(text) == 3

    def test_sorry_in_proof_block(self) -> None:
        text = """
theorem foo : True := by
  have h : Nat := 0
  sorry
"""
        assert count_sorries(text) == 1

    def test_sorry_in_comment_still_counts(self) -> None:
        # Conservative: count sorries in comments too
        text = "-- TODO: remove this sorry\ntheorem foo := sorry"
        assert count_sorries(text) == 2

    def test_does_not_count_partial_matches(self) -> None:
        text = "-- sorrytown is not a placeholder"
        assert count_sorries(text) == 0


class TestCountAdmits:
    """Test admit counting."""

    def test_no_admits(self) -> None:
        text = "theorem foo : True := sorry"
        assert count_admits(text) == 0

    def test_single_admit(self) -> None:
        text = "theorem foo : True := by admit"
        assert count_admits(text) == 1

    def test_multiple_admits(self) -> None:
        text = "admit\nadmit\nadmit"
        assert count_admits(text) == 3


class TestLoopVerification:
    """Test LoopVerification dataclass."""

    def test_is_success_when_compiles_and_no_placeholders(self) -> None:
        v = LoopVerification(
            compiles=True,
            sorry_count_before=1,
            sorry_count_after=0,
            admit_count_before=0,
            admit_count_after=0,
            file_size_before=100,
            file_size_after=100,
        )
        assert v.is_success is True

    def test_is_not_success_when_sorry_remains(self) -> None:
        v = LoopVerification(
            compiles=True,
            sorry_count_before=1,
            sorry_count_after=1,
            admit_count_before=0,
            admit_count_after=0,
            file_size_before=100,
            file_size_after=100,
        )
        assert v.is_success is False

    def test_is_not_success_when_admit_remains(self) -> None:
        v = LoopVerification(
            compiles=True,
            sorry_count_before=0,
            sorry_count_after=0,
            admit_count_before=0,
            admit_count_after=1,
            file_size_before=100,
            file_size_after=100,
        )
        assert v.is_success is False

    def test_is_not_success_when_not_compiling(self) -> None:
        v = LoopVerification(
            compiles=False,
            sorry_count_before=1,
            sorry_count_after=0,
            admit_count_before=0,
            admit_count_after=0,
            file_size_before=100,
            file_size_after=100,
        )
        assert v.is_success is False

    def test_is_not_success_when_file_shrinks_too_much(self) -> None:
        v = LoopVerification(
            compiles=True,
            sorry_count_before=0,
            sorry_count_after=0,
            admit_count_before=0,
            admit_count_after=0,
            file_size_before=100,
            file_size_after=70,  # 30% shrinkage, exceeds 20% limit
        )
        assert v.is_success is False

    def test_is_success_with_acceptable_shrinkage(self) -> None:
        v = LoopVerification(
            compiles=True,
            sorry_count_before=0,
            sorry_count_after=0,
            admit_count_before=0,
            admit_count_after=0,
            file_size_before=100,
            file_size_after=85,  # 15% shrinkage, within limit
        )
        assert v.is_success is True

    def test_sorry_delta(self) -> None:
        v = LoopVerification(
            compiles=True,
            sorry_count_before=3,
            sorry_count_after=1,
            admit_count_before=0,
            admit_count_after=0,
            file_size_before=100,
            file_size_after=100,
        )
        assert v.sorry_delta == -2

    def test_admit_delta(self) -> None:
        v = LoopVerification(
            compiles=True,
            sorry_count_before=0,
            sorry_count_after=0,
            admit_count_before=1,
            admit_count_after=2,
            file_size_before=100,
            file_size_after=100,
        )
        assert v.admit_delta == 1

    def test_is_progress_when_sorry_decreases(self) -> None:
        v = LoopVerification(
            compiles=True,
            sorry_count_before=2,
            sorry_count_after=1,
            admit_count_before=0,
            admit_count_after=0,
            file_size_before=100,
            file_size_after=100,
        )
        assert v.is_progress is True

    def test_is_not_progress_when_sorry_increases(self) -> None:
        v = LoopVerification(
            compiles=True,
            sorry_count_before=1,
            sorry_count_after=2,
            admit_count_before=0,
            admit_count_after=0,
            file_size_before=100,
            file_size_after=100,
        )
        assert v.is_progress is False

    def test_is_not_progress_when_not_compiling(self) -> None:
        v = LoopVerification(
            compiles=False,
            sorry_count_before=2,
            sorry_count_after=1,
            admit_count_before=0,
            admit_count_after=0,
            file_size_before=100,
            file_size_after=100,
        )
        assert v.is_progress is False


class TestLoopExitCondition:
    """Test exit condition determination."""

    def test_success_condition(self) -> None:
        v = LoopVerification(
            compiles=True,
            sorry_count_before=1,
            sorry_count_after=0,
            admit_count_before=0,
            admit_count_after=0,
            file_size_before=100,
            file_size_after=100,
        )
        assert v.exit_condition == LoopExitCondition.SUCCESS

    def test_continue_when_making_progress(self) -> None:
        v = LoopVerification(
            compiles=True,
            sorry_count_before=3,
            sorry_count_after=2,  # Progress but not done
            admit_count_before=0,
            admit_count_after=0,
            file_size_before=100,
            file_size_after=100,
        )
        assert v.exit_condition == LoopExitCondition.CONTINUE

    def test_stalled_when_no_progress(self) -> None:
        v = LoopVerification(
            compiles=True,
            sorry_count_before=1,
            sorry_count_after=1,  # No progress
            admit_count_before=0,
            admit_count_after=0,
            file_size_before=100,
            file_size_after=100,
        )
        assert v.exit_condition == LoopExitCondition.STALLED

    def test_regression_when_file_shrinks(self) -> None:
        v = LoopVerification(
            compiles=True,
            sorry_count_before=0,
            sorry_count_after=0,
            admit_count_before=0,
            admit_count_after=0,
            file_size_before=100,
            file_size_after=50,  # 50% shrinkage
        )
        assert v.exit_condition == LoopExitCondition.REGRESSION

    def test_stalled_when_compilation_fails(self) -> None:
        # Compilation failure without file size change = stalled
        v = LoopVerification(
            compiles=False,
            sorry_count_before=1,
            sorry_count_after=1,
            admit_count_before=0,
            admit_count_after=0,
            file_size_before=100,
            file_size_after=100,
        )
        assert v.exit_condition == LoopExitCondition.STALLED

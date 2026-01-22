"""Unit tests for the search index builder."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from erdos.core.models import ProblemRecord, ProblemStatus
from erdos.core.search.index_builder import build_index


@dataclass(frozen=True)
class _FakeRepo:
    problems: list[ProblemRecord]

    def iter_problems(self):
        yield from self.problems

    def get_by_id(self, problem_id: int):
        return next((p for p in self.problems if p.id == problem_id), None)

    def load_all(self, *, use_cache: bool = True):
        return list(self.problems)


class _FaultyIndex:
    def __init__(self, *, fail_on_id: int) -> None:
        self._fail_on_id = fail_on_id
        self._indexed: list[int] = []

    def clear(self) -> None:
        self._indexed.clear()

    def index_problem(self, problem: ProblemRecord) -> None:
        if problem.id == self._fail_on_id:
            raise RuntimeError("boom")
        self._indexed.append(problem.id)

    def search(
        self, query: str, *, limit: int = 10, problem_id=None, source_types=None
    ):
        return []

    def problem_count(self) -> int:
        return len(set(self._indexed))

    def chunk_count(self) -> int:
        return 0

    def get_stats(self) -> dict[str, object]:
        return {"problems": self.problem_count(), "chunks": self.chunk_count()}


def test_build_index_skips_failed_problem_and_logs(caplog) -> None:
    """build_index logs and skips individual problem indexing failures."""
    repo = _FakeRepo(
        problems=[
            ProblemRecord(
                id=1,
                title="P1",
                statement="S1",
                status=ProblemStatus.OPEN,
            ),
            ProblemRecord(
                id=2,
                title="P2",
                statement="S2",
                status=ProblemStatus.OPEN,
            ),
        ]
    )
    index = _FaultyIndex(fail_on_id=2)

    with caplog.at_level(logging.ERROR):
        result = build_index(loader=repo, index=index)

    assert result["problems_indexed"] == 1
    assert "Failed to index problem 2" in caplog.text

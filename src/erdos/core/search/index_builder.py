"""Build search index from problem data."""

import logging
from typing import Protocol

from erdos.core.ports import (
    ProblemRepository,
    SearchIndexReadPort,
    SearchIndexWritePort,
)


logger = logging.getLogger(__name__)


class SearchIndexBuildPort(SearchIndexReadPort, SearchIndexWritePort, Protocol):
    """Interface needed to build or rebuild the search index."""

    ...


def build_index(
    *,
    loader: ProblemRepository,
    index: SearchIndexBuildPort,
    rebuild: bool = False,
) -> dict[str, object]:
    """
    Build or update the search index.

    Individual problem indexing failures are logged and skipped. This may leave
    the index in a partially-updated state. If you need atomic behavior, you
    could implement a transactional rollback strategy (e.g. rebuild into a
    temporary database and swap on success).

    Args:
        loader: Problem repository
        index: Search index
        rebuild: If True, clear existing index first

    Returns:
        Statistics about the indexing operation
    """
    logger.info("Starting index build (rebuild=%s)", rebuild)

    if rebuild:
        logger.info("Clearing existing index")
        index.clear()

    problems_indexed = 0
    for problem in loader.iter_problems():
        try:
            index.index_problem(problem)
        except Exception as exc:
            logger.error(
                "Failed to index problem %s: %s",
                getattr(problem, "id", "<unknown>"),
                exc,
                exc_info=True,
            )
            continue
        problems_indexed += 1
        if problems_indexed % 100 == 0:
            logger.debug("Indexed %d problems", problems_indexed)

    total_chunks = index.chunk_count()
    logger.info(
        "Index build complete: %d problems indexed, %d total chunks",
        problems_indexed,
        total_chunks,
    )

    return {
        "problems_indexed": problems_indexed,
        "total_chunks": total_chunks,
        "stats": index.get_stats(),
    }

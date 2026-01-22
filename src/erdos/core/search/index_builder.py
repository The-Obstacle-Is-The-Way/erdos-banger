"""Build search index from problem data."""

import logging

from erdos.core.ports import ProblemRepository, SearchIndexProtocol


logger = logging.getLogger(__name__)


def build_index(
    *,
    loader: ProblemRepository,
    index: SearchIndexProtocol,
    rebuild: bool = False,
) -> dict[str, object]:
    """
    Build or update the search index.

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
        index.index_problem(problem)
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

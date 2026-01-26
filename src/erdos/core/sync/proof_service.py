"""Proof sync application service (SPEC-035).

This module contains orchestration for:
- fetching/parsing proof links from the forum
- writing caches/provenance to disk
- optionally verifying proof repositories (via core/sync/proofs.py)

It is intentionally free of Typer/Rich dependencies so it can be unit tested.
"""

from __future__ import annotations

import logging
from pathlib import Path

from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.sync.forum import (
    ForumFetchError,
    fetch_and_parse_forum,
    parse_forum_html,
    save_proof_links_cache,
)
from erdos.core.sync.models import ProofLinksCache, VerificationStatus
from erdos.core.sync.proofs import (
    create_provenance,
    save_provenance,
    save_verification_log,
    verify_proof,
)


logger = logging.getLogger(__name__)


DEFAULT_CACHE_PATH = Path("data/sync_cache/proofs")


def _ensure_cache_dir(cache_path: Path) -> None:
    cache_path.mkdir(parents=True, exist_ok=True)


def _run_verification(
    problem_id: int,
    cache: ProofLinksCache,
    *,
    dry_run: bool,
    cache_path: Path,
) -> CLIOutput:
    """Run verification on extracted proof links.

    Tries each link deterministically until one reaches no_sorries verification.
    Per SPEC-035: keeps the first that reaches verification_strength=no_sorries.
    """
    if not cache.links:
        return CLIOutput.ok(
            command="erdos sync proof",
            data={
                "problem_id": problem_id,
                "links": [],
                "links_count": 0,
                "provenance_path": str(
                    cache_path / str(problem_id) / "provenance.json"
                ),
                "verification_status": "unverified",
                "verification_error": "No proof links found to verify",
            },
        )

    best_result = None
    best_link = None

    priority = {
        VerificationStatus.VERIFIED: 4,
        VerificationStatus.INCONCLUSIVE: 3,
        VerificationStatus.FAILED: 2,
        VerificationStatus.SOURCE_UNAVAILABLE: 1,
        VerificationStatus.UNVERIFIED: 0,
    }
    for link in cache.links:
        logger.info("Verifying %s", link.url)
        result = verify_proof(link, problem_id)

        if best_result is None:
            best_result = result
            best_link = link

        if result.status == VerificationStatus.VERIFIED:
            best_result = result
            best_link = link
            break

        if priority.get(result.status, 0) > priority.get(best_result.status, 0):
            best_result = result
            best_link = link

    if best_result is None or best_link is None:
        return CLIOutput.err(
            command="erdos sync proof",
            error_type="InternalError",
            message="No verification result (unexpected)",
            code=ExitCode.ERROR,
        )

    provenance = create_provenance(problem_id, best_link, best_result).model_copy(
        update={"extracted_at": cache.extracted_at}
    )

    if dry_run:
        provenance_path = cache_path / str(problem_id) / "provenance.json"
    else:
        _ensure_cache_dir(cache_path)
        provenance_path = save_provenance(provenance, cache_dir=cache_path)

        if best_result.log_content:
            log_path = save_verification_log(
                problem_id, best_result.log_content, cache_dir=cache_path
            )
            provenance = provenance.model_copy(
                update={"log_path": str(log_path.relative_to(cache_path.parent.parent))}
            )
            save_provenance(provenance, cache_dir=cache_path)

    return CLIOutput.ok(
        command="erdos sync proof",
        data={
            "problem_id": problem_id,
            "links": [
                {
                    "url": link.url,
                    "author": link.author,
                    "lean_version_hint": link.lean_version_hint,
                }
                for link in cache.links
            ],
            "links_count": len(cache.links),
            "provenance_path": str(provenance_path),
            "verification_status": best_result.status.value,
            "verification_strength": best_result.strength.value,
            "verification_error": best_result.error,
            "verified_repo": best_link.url,
            "verified_commit": best_result.repo_commit,
            "verified_files": best_result.verified_files,
            "toolchain": best_result.toolchain,
        },
    )


def sync_proof_links(
    problem_id: int,
    *,
    dry_run: bool = False,
    verify: bool = False,
    html_content: str | None = None,
    cache_path: Path | None = None,
) -> CLIOutput:
    """Sync proof links from a forum thread (and optionally verify proofs).

    Args:
        problem_id: Problem ID to sync.
        dry_run: If True, do not write to disk.
        verify: If True, clone and verify proofs.
        html_content: Pre-fetched HTML (fixtures/testing).
        cache_path: Override cache directory (fixtures/testing).
    """
    resolved_cache_path = DEFAULT_CACHE_PATH if cache_path is None else cache_path
    cached = html_content is not None

    try:
        if html_content is not None:
            cache = parse_forum_html(html_content, problem_id)
        else:
            cache = fetch_and_parse_forum(problem_id)

        if not dry_run:
            _ensure_cache_dir(resolved_cache_path)
            save_proof_links_cache(cache, cache_dir=resolved_cache_path)

        if verify:
            return _run_verification(
                problem_id,
                cache,
                dry_run=dry_run,
                cache_path=resolved_cache_path,
            )

        provenance_path = resolved_cache_path / str(problem_id) / "provenance.json"
        if cache.links:
            provenance = create_provenance(
                problem_id, cache.links[0], verification=None
            ).model_copy(update={"extracted_at": cache.extracted_at})
            if not dry_run:
                _ensure_cache_dir(resolved_cache_path)
                save_provenance(provenance, cache_dir=resolved_cache_path)

        return CLIOutput.ok(
            command="erdos sync proof",
            data={
                "problem_id": problem_id,
                "links": [
                    {
                        "url": link.url,
                        "author": link.author,
                        "lean_version_hint": link.lean_version_hint,
                    }
                    for link in cache.links
                ],
                "links_count": len(cache.links),
                "provenance_path": str(provenance_path),
                "cached": cached,
                "verification_status": "unverified",
            },
        )

    except ForumFetchError as e:
        code = ExitCode.NETWORK_ERROR if e.status_code != 404 else ExitCode.NOT_FOUND
        return CLIOutput.err(
            command="erdos sync proof",
            error_type="FetchError",
            message=str(e),
            code=code,
        )
    except Exception as e:  # safety net; convert unexpected failures to CLIOutput
        logger.exception("Unexpected error in sync proof")
        return CLIOutput.err(
            command="erdos sync proof",
            error_type="UnexpectedError",
            message=str(e),
            code=ExitCode.ERROR,
        )

"""CLI helpers for accessing the application context."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    import typer

from erdos.core.context import AppContext
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.problem_loader import ProblemLoaderError
from erdos.core.search.db import SearchIndexError


def get_app_context(
    ctx: typer.Context,
    *,
    command: str,
    require_index: bool = False,
) -> tuple[AppContext, None] | tuple[None, CLIOutput]:
    """Get (and cache) the AppContext on ctx.obj.

    Returns:
        (context, None) on success.
        (None, error) on failure.

    Usage::

        app_ctx, app_error = get_app_context(ctx, command="erdos show")
        if app_error is not None:
            exit_with_result(ctx, app_error)
            return
        # At this point, app_ctx is guaranteed to be non-None
    """
    ctx.ensure_object(dict)
    obj: dict[str, Any]
    if isinstance(ctx.obj, dict):
        obj = ctx.obj
    else:
        obj = {}
        ctx.obj = obj

    existing = obj.get("app_context")
    if isinstance(existing, AppContext):
        app_ctx = existing
    else:
        try:
            app_ctx = AppContext.from_environment()
        except ProblemLoaderError as e:
            return None, CLIOutput.err(
                command=command,
                error_type="LoaderError",
                message=str(e),
                code=ExitCode.ERROR,
            )
        obj["app_context"] = app_ctx

    if require_index:
        try:
            app_ctx.ensure_index()
        except SearchIndexError as e:
            return None, CLIOutput.err(
                command=command,
                error_type="IndexError",
                message=str(e),
                code=ExitCode.ERROR,
            )

    return app_ctx, None

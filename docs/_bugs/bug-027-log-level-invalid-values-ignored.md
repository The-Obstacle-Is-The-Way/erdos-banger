# Bug: `--log-level` accepts invalid values without error

**Priority:** P3
**Status:** Open
**Found:** 2026-01-25
**Fixed:** (not yet)
**Commit:** (pending)

## Description

The global `--log-level` flag accepts arbitrary invalid values like `INVALID`, `foo`, or `DEBUG123` without any validation error, silently ignoring them.

## Steps to Reproduce

1. Run `uv run erdos --log-level INVALID list --limit 2`
2. Run `uv run erdos --log-level foo list --limit 2`

## Expected Behavior

A validation error like:
```
Invalid value for '--log-level': 'INVALID' is not one of 'DEBUG', 'INFO', 'WARN', 'ERROR'.
```

## Actual Behavior

The command runs successfully without any error or warning, presumably using the default log level.

## Root Cause

The `--log-level` flag in `src/erdos/cli.py` or the app callback doesn't validate that the value is one of the documented valid options (DEBUG, INFO, WARN, ERROR). It likely passes the invalid value to Python's logging module which ignores unrecognized levels.

## Fix

Add validation using Typer's `enum` or `click.Choice`:

```python
log_level: Annotated[
    str,
    typer.Option(
        "--log-level",
        help="Logging level: DEBUG, INFO, WARN, ERROR.",
        case_sensitive=False,
    ),
] = "INFO",

# In the callback:
valid_levels = {"DEBUG", "INFO", "WARN", "WARNING", "ERROR"}
if log_level.upper() not in valid_levels:
    raise typer.BadParameter(f"Invalid log level: {log_level}")
```

Or use an enum:

```python
class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"

log_level: Annotated[LogLevel, typer.Option("--log-level")] = LogLevel.INFO
```

## Related

- `src/erdos/cli.py` (global options)
- Help text: `--log-level TEXT  Logging level: DEBUG, INFO, WARN, ERROR.`

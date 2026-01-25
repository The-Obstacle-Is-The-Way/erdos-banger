# Bug: `--log-level` accepts invalid values without error

**Priority:** P3
**Status:** Fixed
**Found:** 2026-01-25
**Fixed:** 2026-01-25
**Commit:** 92039ca

## Description

The global `--log-level` flag accepts arbitrary invalid values like `INVALID`, `foo`, or `DEBUG123` without any validation error, silently ignoring them.

## Steps to Reproduce

1. Run `uv run erdos --log-level INVALID list --limit 2`
2. Run `uv run erdos --log-level foo list --limit 2`

## Expected Behavior

A validation error like:
```
Invalid value for '--log-level': 'INVALID' is not one of 'debug', 'info', 'warn', 'error'.
```

## Actual Behavior

The command runs successfully without any error or warning, presumably using the default log level.

## Root Cause

The `--log-level` flag was a plain string. `_configure_logging()` mapped known values and fell back to `INFO` for unknown values, so invalid inputs were silently ignored.

## Fix

Use a Typer enum so Click validates the value:

```python
class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"

log_level: Annotated[
    LogLevel, typer.Option("--log-level", case_sensitive=False)
] = LogLevel.INFO
```

## Related

- `src/erdos/cli.py` (global options)

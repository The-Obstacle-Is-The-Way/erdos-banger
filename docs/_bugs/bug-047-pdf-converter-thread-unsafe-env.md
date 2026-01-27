# BUG-047: PDF Converter Thread-Unsafe Environment Mutation

**Priority:** P1
**Status:** Open
**Found:** 2026-01-27
**Component:** `src/erdos/core/pdf/converter.py`

## Description

The PDF converter mutates `os.environ` directly to set `TORCH_DEVICE` before conversion. This is thread-unsafe and can cause race conditions in concurrent conversions.

## Steps to Reproduce

1. Run two concurrent PDF conversions with different `torch_device` settings
2. The second conversion may use the first's `TORCH_DEVICE` setting

## Evidence

```python
# src/erdos/core/pdf/converter.py:395-419
original_torch_device = os.environ.get("TORCH_DEVICE")
try:
    os.environ["TORCH_DEVICE"] = config.torch_device  # RACE CONDITION!
    # ... conversion code ...
finally:
    os.environ.pop("TORCH_DEVICE", None)
    if original_torch_device is not None:
        os.environ["TORCH_DEVICE"] = original_torch_device
```

## Expected Behavior

Each conversion should use its own `TORCH_DEVICE` setting without affecting other concurrent conversions.

## Actual Behavior

Global `os.environ` is mutated, causing race conditions between concurrent conversions.

## Root Cause

Direct mutation of global `os.environ` instead of passing environment through subprocess parameters.

## Recommended Fix

```python
# Pass torch_device via subprocess env parameter instead
def _get_conversion_env(config: PDFConversionConfig) -> dict[str, str]:
    env = dict(os.environ)
    if config.torch_device:
        env["TORCH_DEVICE"] = config.torch_device
    return env

# Use: subprocess.run(..., env=_get_conversion_env(config))
```

## Impact

- High: Could cause incorrect device selection in production
- Affects: Multi-threaded/async PDF conversion workflows
- Workaround: Run conversions sequentially (performance impact)

## Related

- DEBT-114: Hardcoded relative paths (same module)
- AUDIT-011: Thread-unsafe environment mutation

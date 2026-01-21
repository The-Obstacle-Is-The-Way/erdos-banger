# DEBT-036: Marker PDF Converter Device Selection Not Exposed

**Status:** Fixed
**Severity:** P3 (performance/DevX; not a correctness bug)
**Found:** 2026-01-21
**Found By:** Post-Ralph adversarial audit
**Fixed In:** 7005b65

---

## Summary

The SPEC-019 PDF conversion implementation uses Marker but does not provide a first-class way to select the underlying torch device (CPU/CUDA/MPS). This is primarily a **performance/DevX** issue for contributors on Apple Silicon or GPU machines.

## Current State

`src/erdos/core/pdf_converter.py` does not set `TORCH_DEVICE` and the CLI does not expose a `--torch-device` (or equivalent) knob. Users must discover/remember the environment-variable override themselves.

## Evidence

From Marker’s upstream docs (repo README):

> The torch device will be automatically detected, but you can override this by setting the `TORCH_DEVICE` environment variable.

From [PyTorch MPS documentation](https://developer.apple.com/metal/pytorch/):

> MPS backend enables GPU acceleration on Apple Silicon through Apple's Metal framework.

## Fix Required

### Option A: Documentation-only (Lowest effort)

Document that users should set:
```bash
export TORCH_DEVICE=mps  # Apple Silicon (if supported by your PyTorch build)
export TORCH_DEVICE=cuda # NVIDIA
```

### Option B: Runtime Detection

Add auto-detection in `pdf_converter.py`:

```python
import platform
import torch

def _get_torch_device() -> str:
    """Detect best available torch device."""
    if torch.cuda.is_available():
        return "cuda"
    if platform.system() == "Darwin" and platform.processor() == "arm":
        # Apple Silicon - check MPS availability
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    return "cpu"
```

### Option C: CLI Flag (Best DX)

Add `--device` option to `erdos convert`:
```bash
erdos convert paper.pdf --device mps
```

### Chosen Approach (This Deck)

Implement **Option C (CLI flag)** and keep the environment-variable override documented.

Rationale:
- Deterministic and CI-testable (no Apple hardware required).
- Marker already supports `TORCH_DEVICE`; we just expose a stable knob.
- Avoids platform-specific autodetection heuristics that drift over time.

## Caveats

MPS support depends on your local PyTorch build and workload. Some operations may be unsupported or slower than CPU for specific models. If you see runtime errors with `TORCH_DEVICE=mps`, fall back to `TORCH_DEVICE=cpu`.

## Acceptance Criteria

1. [x] `erdos convert --help` documents a new `--device` option (examples included).
2. [x] `erdos convert --device <cpu|cuda|mps>` sets `TORCH_DEVICE=<...>` for Marker conversions.
3. [x] `PDFConversionConfig` carries the selected device (e.g., `torch_device: str | None`) and `convert_pdf()` honors it when using Marker.
4. [x] Tests:
   - [x] `tests/integration/test_pdf_convert.py` asserts `--device` appears in help output (via `strip_ansi`).
   - [x] `tests/unit/test_pdf_converter.py` verifies the env-var wiring via `monkeypatch` (no Marker install required).
5. [x] `make ci` passes.

## Testing

```bash
# CI-safe sanity (does not require Marker installed)
uv run erdos convert --help | rg -- '--device'

# Manual (only if you have Marker + torch configured)
TORCH_DEVICE=mps uv run erdos convert test.pdf -o test.md
```

---

## References

- [Marker docs](https://github.com/datalab-to/marker)
- [PyTorch MPS Backend](https://developer.apple.com/metal/pytorch/)
- [Accelerated PyTorch on Mac](https://pytorch.org/blog/introducing-accelerated-pytorch-training-on-mac/)

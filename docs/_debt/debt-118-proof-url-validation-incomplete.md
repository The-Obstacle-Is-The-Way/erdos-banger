# DEBT-118: Proof Repository URL Validation Incomplete

**Priority:** P1
**Status:** Open
**Found:** 2026-01-27
**Component:** `src/erdos/core/sync/proofs.py`

## Summary

URL validation for proof repositories only checks for `https://` prefix. Malformed URLs, non-GitHub/GitLab hosts, or URLs with injection characters could be passed to git clone.

## Evidence

```python
# src/erdos/core/sync/proofs.py:119-120
if not url.startswith("https://"):
    return CloneResult(success=False, error="Only HTTPS URLs are allowed")
# URL is then passed directly to git clone
```

## Security Concern

While git clone itself validates URLs, incomplete validation could:
1. Allow unexpected hosts (not just github.com/gitlab.com)
2. Pass URLs with special characters
3. Leak error messages with URL details

## Recommended Fix

```python
from urllib.parse import urlparse

ALLOWED_HOSTS = frozenset({"github.com", "gitlab.com"})

def _validate_repo_url(url: str) -> tuple[bool, str | None]:
    """Validate repository URL for security.

    Returns:
        (is_valid, error_message)
    """
    if not url.startswith("https://"):
        return False, "Only HTTPS URLs are allowed"

    try:
        parsed = urlparse(url)
    except ValueError as e:
        return False, f"Invalid URL format: {e}"

    if parsed.scheme != "https":
        return False, "Only HTTPS URLs are allowed"

    if not parsed.hostname:
        return False, "URL must have a valid host"

    # Reject URLs with embedded credentials (security risk)
    if parsed.username or parsed.password:
        return False, "Credentials are not allowed in repository URLs"

    # Reject explicit ports (security boundary should be host-based only)
    try:
        port = parsed.port
    except ValueError:
        return False, "Invalid port in URL"
    if port is not None:
        return False, "Ports are not allowed in repository URLs"

    host = parsed.hostname.lower()
    if host not in ALLOWED_HOSTS:
        return False, f"Only {', '.join(sorted(ALLOWED_HOSTS))} repositories are allowed"

    if not parsed.path or parsed.path == "/":
        return False, "URL must include repository path"

    return True, None
```

## Impact

- High: Security boundary for external code execution
- Affects: `erdos sync proofs verify` command
- Current: Relies on git's URL validation (probably fine, but defense-in-depth)

## Related

- AUDIT-017: Proof repository URL validation
- Environment sanitization in same module (which IS thorough)

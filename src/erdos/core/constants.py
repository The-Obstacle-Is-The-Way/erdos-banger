"""Application-wide constants for erdos-banger CLI toolkit."""

# --- Preview and truncation lengths (characters) ---

PREVIEW_LENGTH = 200
"""Default length for text previews and snippets."""

MESSAGE_TRUNCATION = 500
"""Maximum length for error messages and debug output."""

TITLE_TRUNCATION = 50
"""Maximum length for title displays."""

TEXT_PREVIEW_LENGTH = 100
"""Length for short text previews in ask command."""

# --- Timeouts (seconds) ---

DEFAULT_HTTP_TIMEOUT = 30.0
"""Default timeout for HTTP requests to arXiv and Crossref APIs."""

LEAN_TOOLCHAIN_VERSION = "v4.12.0"
"""Pinned Lean toolchain / mathlib version tag (keep in sync with formal/lean/lean-toolchain)."""

LEAN_COMPILE_TIMEOUT = 120
"""Timeout for Lean compilation operations."""

LEAN_VERSION_TIMEOUT = 10
"""Timeout for `lean --version` environment checks."""

LAKE_UPDATE_TIMEOUT = 600
"""Timeout for long-running Lean tool operations (e.g., `lake update`, Aristotle)."""

LLM_COMMAND_TIMEOUT = 300
"""Timeout for external LLM command execution (5 minutes)."""

GIT_OP_TIMEOUT = 30
"""Timeout for fast git operations (rev-parse, status, rev-list)."""

GIT_FETCH_TIMEOUT = 120
"""Timeout for git network operations (fetch, clone, checkout)."""

# --- Rate limiting ---

API_RATE_LIMIT_DELAY = 3.0
"""Delay (seconds) between processing references during ingestion.

Applied per-reference, not per-request. Each reference may make 1-3 requests
(DOI lookup, arXiv metadata, arXiv source download). This delay satisfies
typical API rate limits (Crossref, arXiv recommend ~3s between requests).
"""

# --- Search defaults ---

DEFAULT_SEARCH_LIMIT = 10
"""Default number of search results to return."""

DEFAULT_RAG_LIMIT = 5
"""Default number of RAG context chunks to retrieve."""

MAX_QUERY_TERMS = 25
"""Maximum number of query terms to extract from user questions."""

# --- Size limits ---

ASK_PROMPT_MAX_BYTES = 32_000
"""Maximum UTF-8 byte size for `erdos ask` prompts.

This is a hard cap to prevent downstream LLM context-limit failures and timeouts
when sources contain large blobs (e.g., PDF extractions or long synthesis).
"""

MAX_TEX_FILE_SIZE = 2 * 1024 * 1024
"""Maximum LaTeX file size to process (2 MiB)."""

# --- Retry configuration ---

RETRY_MAX_ATTEMPTS = 3
"""Maximum number of attempts for transient network errors."""

RETRY_BASE_DELAY = 2.0
"""Base delay (seconds) between retry attempts. Exponential backoff uses 2^attempt."""

RETRY_MAX_DELAY = 30.0
"""Maximum delay (seconds) between retry attempts."""

RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
"""HTTP status codes that warrant a retry (rate limit + server errors)."""

"""Formal conjectures integration for importing upstream Lean formalizations.

This package handles:
1. Parsing upstream formalization metadata from teorth/erdosproblems
2. Fetching Lean files from google-deepmind/formal-conjectures
3. Comparing local vs upstream formalizations
4. Tracking provenance of imported files
"""

from __future__ import annotations

from erdos.core.formal_conjectures.config import (
    FORMAL_CONJECTURES_BASE_URL,
    FORMAL_CONJECTURES_REPO,
    FormalConjecturesError,
)
from erdos.core.formal_conjectures.fetch import (
    FetchResult,
    fetch_upstream_lean_file,
)
from erdos.core.formal_conjectures.local import (
    LocalFormalizationInfo,
    compute_file_sha256,
    has_sorry,
)
from erdos.core.formal_conjectures.paths import (
    build_upstream_url,
    get_cache_path,
    get_local_file_path,
)
from erdos.core.formal_conjectures.provenance import (
    ProvenanceEntry,
    ProvenanceFile,
    load_provenance,
    save_provenance,
)
from erdos.core.formal_conjectures.upstream import (
    UpstreamFormalizationInfo,
    load_upstream_metadata,
    parse_upstream_formalization_status,
)


__all__ = [
    "FORMAL_CONJECTURES_BASE_URL",
    "FORMAL_CONJECTURES_REPO",
    "FetchResult",
    "FormalConjecturesError",
    "LocalFormalizationInfo",
    "ProvenanceEntry",
    "ProvenanceFile",
    "UpstreamFormalizationInfo",
    "build_upstream_url",
    "compute_file_sha256",
    "fetch_upstream_lean_file",
    "get_cache_path",
    "get_local_file_path",
    "has_sorry",
    "load_provenance",
    "load_upstream_metadata",
    "parse_upstream_formalization_status",
    "save_provenance",
]

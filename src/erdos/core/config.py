"""Centralized application configuration.

This module is the single source of truth for environment-based configuration.
All os.environ reads for application settings should be centralized here.

Usage:
    # In composition root (context.py or CLI entry points):
    config = AppConfig.from_env()

    # Pass config to services via constructors or AppContext:
    loader = ProblemLoader(config.data_path)
    index = SearchIndex(config.index_path)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


# Default values (matching existing behavior)
DEFAULT_MAILTO = "erdos-banger@example.com"
DEFAULT_HTTP_TIMEOUT = 30.0
DEFAULT_RUN_LOG_PATH = Path("logs/runs.jsonl")
DEFAULT_INDEX_PATH = Path("index/erdos.sqlite")
DEFAULT_ARISTOTLE_COMMAND = "aristotle"


@dataclass(frozen=True)
class AppConfig:
    """Immutable application configuration container.

    This dataclass centralizes all environment-based configuration. It is
    frozen (immutable) to prevent accidental mutation after construction.

    Attributes:
        data_path: Path to problems YAML (from ERDOS_DATA_PATH).
        index_path: Path to SQLite search index (from ERDOS_INDEX_PATH).
        run_log_path: Path to run log file (from ERDOS_RUN_LOG_PATH).
        repo_root: Repository root path (from ERDOS_REPO_ROOT).
        mailto: Contact email for API polite pools (from ERDOS_MAILTO).
        llm_command: External LLM command (from ERDOS_LLM_COMMAND).
        aristotle_api_key: Aristotle API key (from ARISTOTLE_API_KEY).
        aristotle_command: Path to aristotle CLI (from ERDOS_ARISTOTLE_COMMAND).
        openalex_api_key: OpenAlex API key (from OPENALEX_API_KEY).
        http_timeout: Default HTTP timeout in seconds.
    """

    # Paths (None means use runtime defaults)
    data_path: Path | None = None
    index_path: Path | None = None
    run_log_path: Path = field(default=DEFAULT_RUN_LOG_PATH)
    repo_root: Path | None = None

    # API configuration
    mailto: str = DEFAULT_MAILTO
    llm_command: str = ""
    aristotle_api_key: str = ""
    aristotle_command: str = DEFAULT_ARISTOTLE_COMMAND
    openalex_api_key: str = ""

    # Network
    http_timeout: float = DEFAULT_HTTP_TIMEOUT

    @classmethod
    def from_env(cls) -> AppConfig:
        """Create configuration from environment variables.

        This is the single place where os.environ reads occur for application
        configuration. All environment variable names and defaults are defined here.

        Environment variables:
            ERDOS_DATA_PATH: Path to problems YAML file or directory.
            ERDOS_INDEX_PATH: Path to SQLite search index file.
            ERDOS_RUN_LOG_PATH: Path to run log JSONL file.
            ERDOS_REPO_ROOT: Repository root directory.
            ERDOS_MAILTO: Contact email for API polite pools.
            ERDOS_LLM_COMMAND: External LLM command for ask/loop.
            ARISTOTLE_API_KEY: API key for Aristotle LLM service.
            ERDOS_ARISTOTLE_COMMAND: Path to aristotle CLI binary.
            OPENALEX_API_KEY: API key for OpenAlex polite pool.

        Returns:
            AppConfig instance with values from environment.
        """
        # Read paths (None if not set)
        data_path_str = os.environ.get("ERDOS_DATA_PATH")
        index_path_str = os.environ.get("ERDOS_INDEX_PATH")
        run_log_path_str = os.environ.get("ERDOS_RUN_LOG_PATH")
        repo_root_str = os.environ.get("ERDOS_REPO_ROOT")

        return cls(
            data_path=Path(data_path_str) if data_path_str else None,
            index_path=Path(index_path_str) if index_path_str else None,
            run_log_path=(
                Path(run_log_path_str) if run_log_path_str else DEFAULT_RUN_LOG_PATH
            ),
            repo_root=Path(repo_root_str) if repo_root_str else None,
            mailto=os.environ.get("ERDOS_MAILTO", DEFAULT_MAILTO),
            llm_command=os.environ.get("ERDOS_LLM_COMMAND", ""),
            aristotle_api_key=os.environ.get("ARISTOTLE_API_KEY", "").strip(),
            aristotle_command=os.environ.get(
                "ERDOS_ARISTOTLE_COMMAND", DEFAULT_ARISTOTLE_COMMAND
            ).strip(),
            openalex_api_key=os.environ.get("OPENALEX_API_KEY", ""),
        )

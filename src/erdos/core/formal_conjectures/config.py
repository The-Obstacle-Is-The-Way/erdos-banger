"""Configuration constants for formal conjectures integration."""

from __future__ import annotations


# Source repository constants
FORMAL_CONJECTURES_REPO = "google-deepmind/formal-conjectures"
FORMAL_CONJECTURES_BASE_URL = (
    "https://raw.githubusercontent.com/google-deepmind/formal-conjectures/main/"
)


class FormalConjecturesError(Exception):
    """Error raised by formal_conjectures operations."""

    def __init__(self, message: str, *, error_type: str = "Error") -> None:
        super().__init__(message)
        self.error_type = error_type

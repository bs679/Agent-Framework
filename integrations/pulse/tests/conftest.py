"""Shared test configuration."""

import os

# Ensure executive session keywords are set for tests
os.environ.setdefault(
    "EXECUTIVE_SESSION_KEYWORDS",
    "executive session,exec session,board executive",
)

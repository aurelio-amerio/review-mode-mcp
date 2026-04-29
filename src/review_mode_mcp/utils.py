"""Utility functions: path normalization and ID generation."""

from __future__ import annotations

import random
import re
import string


def normalize_path(relative_path: str) -> str:
    """Convert a relative file path to a flat folder name.

    Replicates the VS Code extension logic:
        relativePath.replace(/[\\\\/\\.]/g, '_')

    Example:
        ``docs/plans/my-plan.md`` → ``docs_plans_my-plan_md``
    """
    return re.sub(r"[\\/.]", "_", relative_path)


def generate_id() -> str:
    """Generate a 7-character random base-36 ID.

    Mirrors the extension's ``Math.random().toString(36).substring(2, 9)``.
    """
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choices(chars, k=7))

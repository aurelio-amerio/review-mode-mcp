"""Utility functions: path normalization and ID generation."""

from __future__ import annotations

import hashlib
import random
import re
import string
from pathlib import Path


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


def external_folder_name(abs_path: str) -> str:
    """Deterministic folder name for files outside the workspace.

    Uses the file's basename (without extension) plus the first 8 characters
    of the SHA-256 hex digest of the normalised absolute path.

    The normalisation step (lowercase, forward slashes) ensures that the
    same file always produces the same hash on Windows regardless of how
    the path separators or casing were passed.

    Example::

        basic-python-ledger_9d4da9ce_a3f1c9b2
    """
    normalized = abs_path.replace("\\", "/").lower()
    short_hash = hashlib.sha256(normalized.encode()).hexdigest()[:8]
    basename = Path(abs_path).stem
    return f"{basename}_{short_hash}"

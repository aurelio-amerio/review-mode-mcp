"""FastMCP server exposing Review Mode annotation tools.

Usage::

    review-mode-mcp --workspace /path/to/project
    review-mode-mcp --workspace . --revisions-dir .my-revisions
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from review_mode_mcp import revisions
from review_mode_mcp.utils import generate_id, normalize_path

# ---------------------------------------------------------------------------
# Module-level state (set once in main(), read by tool handlers)
# ---------------------------------------------------------------------------

_workspace: Path = Path(".")
_revisions_dir: str = ".revisions"

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

mcp = FastMCP("review-mode")

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


def _get_workspace(workspace: str) -> Path:
    return Path(workspace).resolve()


@mcp.tool()
def open_review(file_path: str, workspace: str) -> str:
    """Open a file in Review Mode inside VS Code.

    Writes a UI directive file that the VS Code extension picks up
    automatically via a filesystem watcher. Works in local, WSL,
    DevContainer, and SSH Remote environments — no CLI dependency required.

    Args:
        file_path: Relative path to the file (e.g. "docs/plan.md").
        workspace: Explicit workspace path.
    """
    effective_workspace = _get_workspace(workspace)
    abs_path = str((effective_workspace / file_path).resolve())

    directive = {
        "_ui_directive": True,
        "command_id": "reviewMode.open",
        "args": [abs_path],
    }

    directives_dir = effective_workspace / _revisions_dir / ".directives"
    try:
        directives_dir.mkdir(parents=True, exist_ok=True)
        directive_file = directives_dir / f"{generate_id()}.json"
        directive_file.write_text(json.dumps(directive), encoding="utf-8")
    except OSError as exc:
        return f"Error: could not write directive file — {exc}"

    return f"Directive sent. Review Mode will open '{file_path}' shortly."


@mcp.tool()
def list_reviewed_files(workspace: str) -> list[dict]:
    """List all files in the workspace that have reviews.

    Returns an array of objects with file_path, revision_count,
    total_annotations, open_count, and last_review_date.

    Args:
        workspace: Explicit workspace path.
    """
    effective_workspace = _get_workspace(workspace)
    return revisions.list_reviewed_files(effective_workspace, _revisions_dir)


@mcp.tool()
def get_review_summary(file_path: str, workspace: str) -> dict:
    """Return summary metadata for a file's review.

    Includes revision_count, latest_revision, comment counts by status
    (open, in_progress, resolved, wont_fix), and last_review_date.

    Args:
        file_path: Relative path to the reviewed file.
        workspace: Explicit workspace path.
    """
    effective_workspace = _get_workspace(workspace)
    return revisions.get_review_summary(effective_workspace, _revisions_dir, file_path)


@mcp.tool()
def get_annotations(file_path: str, workspace: str) -> list[dict]:
    """Return the full annotation array from the latest revision of a file.

    Each annotation contains id, startLine, endLine, textPreview,
    priority, status, and thread[].

    Args:
        file_path: Relative path to the reviewed file.
        workspace: Explicit workspace path.
    """
    effective_workspace = _get_workspace(workspace)
    return revisions.get_annotations(effective_workspace, _revisions_dir, file_path)


@mcp.tool()
def update_annotation(
    file_path: str,
    annotation_ids: list[str],
    workspace: str,
    status: Optional[str] = None,
    message: Optional[str] = None,
) -> str:
    """Update the status and/or add an agent reply to one or more annotations.

    At least one of status or message must be provided.

    Args:
        file_path: Relative path to the reviewed file.
        annotation_ids: List of annotation IDs to update.
        workspace: Explicit workspace path.
        status: New status (open, in-progress, resolved, wont-fix).
        message: Reply text (auto-prefixed with [AGENT]).
    """
    effective_workspace = _get_workspace(workspace)
    count = revisions.update_annotations(
        effective_workspace, _revisions_dir, file_path, annotation_ids, status, message
    )
    return f"Updated {count} annotation(s)."


@mcp.tool()
def create_annotation(
    file_path: str,
    line: int,
    message: str,
    workspace: str,
    priority: str = "none",
    status: str = "open",
) -> dict:
    """Create a new annotation on a specific line of the reviewed file.

    Args:
        file_path: Relative path to the reviewed file.
        line: Line number to annotate (1-indexed).
        message: Comment text (auto-prefixed with [AGENT]).
        workspace: Explicit workspace path.
        priority: Priority level (none, low, medium, high, urgent).
        status: Initial status (open, in-progress, resolved, wont-fix).
    """
    effective_workspace = _get_workspace(workspace)
    return revisions.create_annotation(
        effective_workspace, _revisions_dir, file_path, line, message, priority, status
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse CLI arguments and start the MCP server."""
    parser = argparse.ArgumentParser(
        prog="review-mode-mcp",
        description="MCP server for Review Mode — manage review annotations from any AI agent.",
    )
    parser.add_argument(
        "--workspace",
        default=".",
        help="Path to the project workspace root (default: current directory).",
    )
    parser.add_argument(
        "--revisions-dir",
        default=".revisions",
        help="Name of the revisions directory (default: .revisions).",
    )

    args = parser.parse_args()

    global _workspace, _revisions_dir
    _workspace = Path(args.workspace).resolve()
    _revisions_dir = args.revisions_dir

    mcp.run()


if __name__ == "__main__":
    main()

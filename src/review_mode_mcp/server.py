"""FastMCP server exposing Review Mode annotation tools.

Usage::

    review-mode-mcp --workspace /path/to/project
    review-mode-mcp --workspace . --revisions-dir .my-revisions
    review-mode-mcp --workspace . --code-command cursor
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import urllib.parse
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from review_mode_mcp import revisions

# ---------------------------------------------------------------------------
# Module-level state (set once in main(), read by tool handlers)
# ---------------------------------------------------------------------------

_workspace: Path = Path(".")
_revisions_dir: str = ".revisions"
_code_command: str = "code"

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

mcp = FastMCP("review-mode")

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


def _get_workspace(workspace_override: Optional[str]) -> Path:
    return Path(workspace_override).resolve() if workspace_override else _workspace


@mcp.tool()
def open_review(file_path: str, workspace: Optional[str] = None) -> str:
    """Open a file in Review Mode inside VS Code (or compatible editor).

    Invokes the editor's URI handler to open the review panel for the file.

    Args:
        file_path: Relative path to the file (e.g. "docs/plan.md").
        workspace: Optional explicit workspace path to override the server default.
    """
    encoded = urllib.parse.quote(file_path, safe="")
    # If the user passes workspace, we might want to include it in the URI, 
    # but the VS Code extension currently only expects 'path'. 
    # We will pass the same URI. The extension uses the active window's workspace.
    uri = f"vscode://aurelio-amerio.review-mode/open?path={encoded}"

    try:
        subprocess.run(
            [_code_command, "--open-url", uri],
            check=True,
            capture_output=True,
            timeout=10,
        )
    except FileNotFoundError:
        return (
            f"Error: '{_code_command}' command not found on PATH. "
            f"Use --code-command to specify the editor executable "
            f"(e.g. --code-command cursor)."
        )
    except subprocess.CalledProcessError as exc:
        return f"Error opening review: {exc.stderr.decode().strip()}"

    return f"Opened '{file_path}' in Review Mode."


@mcp.tool()
def list_reviewed_files(workspace: Optional[str] = None) -> list[dict]:
    """List all files in the workspace that have reviews.

    Returns an array of objects with file_path, revision_count,
    total_annotations, open_count, and last_review_date.

    Args:
        workspace: Optional explicit workspace path to override the server default.
    """
    effective_workspace = _get_workspace(workspace)
    return revisions.list_reviewed_files(effective_workspace, _revisions_dir)


@mcp.tool()
def get_review_summary(file_path: str, workspace: Optional[str] = None) -> dict:
    """Return summary metadata for a file's review.

    Includes revision_count, latest_revision, comment counts by status
    (open, in_progress, resolved, wont_fix), and last_review_date.

    Args:
        file_path: Relative path to the reviewed file.
        workspace: Optional explicit workspace path to override the server default.
    """
    effective_workspace = _get_workspace(workspace)
    return revisions.get_review_summary(effective_workspace, _revisions_dir, file_path)


@mcp.tool()
def get_annotations(file_path: str, workspace: Optional[str] = None) -> list[dict]:
    """Return the full annotation array from the latest revision of a file.

    Each annotation contains id, startLine, endLine, textPreview,
    priority, status, and thread[].

    Args:
        file_path: Relative path to the reviewed file.
        workspace: Optional explicit workspace path to override the server default.
    """
    effective_workspace = _get_workspace(workspace)
    return revisions.get_annotations(effective_workspace, _revisions_dir, file_path)


@mcp.tool()
def update_annotation(
    file_path: str,
    annotation_ids: list[str],
    status: Optional[str] = None,
    message: Optional[str] = None,
    workspace: Optional[str] = None,
) -> str:
    """Update the status and/or add an agent reply to one or more annotations.

    At least one of status or message must be provided.

    Args:
        file_path: Relative path to the reviewed file.
        annotation_ids: List of annotation IDs to update.
        status: New status (open, in-progress, resolved, wont-fix).
        message: Reply text (auto-prefixed with [AGENT]).
        workspace: Optional explicit workspace path to override the server default.
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
    priority: str = "none",
    status: str = "open",
    workspace: Optional[str] = None,
) -> dict:
    """Create a new annotation on a specific line of the reviewed file.

    Args:
        file_path: Relative path to the reviewed file.
        line: Line number to annotate (1-indexed).
        message: Comment text (auto-prefixed with [AGENT]).
        priority: Priority level (none, low, medium, high, urgent).
        status: Initial status (open, in-progress, resolved, wont-fix).
        workspace: Optional explicit workspace path to override the server default.
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
    parser.add_argument(
        "--code-command",
        default="code",
        help=(
            "Editor CLI command for open_review "
            "(default: code). Use 'cursor', 'windsurf', etc. for VS Code forks."
        ),
    )

    args = parser.parse_args()

    global _workspace, _revisions_dir, _code_command
    _workspace = Path(args.workspace).resolve()
    _revisions_dir = args.revisions_dir
    _code_command = args.code_command

    mcp.run()


if __name__ == "__main__":
    main()

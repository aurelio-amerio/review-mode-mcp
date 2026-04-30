"""Data layer for reading/writing the ``.revisions/`` directory.

All functions operate directly on the filesystem, producing and consuming
plain dicts that match the JSON schema used by the VS Code extension.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from review_mode_mcp.utils import external_folder_name, generate_id, normalize_path

# ---------------------------------------------------------------------------
# Types (mirroring annotationStore.ts)
# ---------------------------------------------------------------------------

# Priority = Literal["none", "low", "medium", "high", "urgent"]
# Status   = Literal["open", "in-progress", "resolved", "wont-fix"]

VALID_PRIORITIES = {"none", "low", "medium", "high", "urgent"}
VALID_STATUSES = {"open", "in-progress", "resolved", "wont-fix"}


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _get_file_revisions_dir(
    workspace: Path, revisions_dir: str, file_path: str
) -> Path:
    """Return the directory inside ``.revisions/`` for *file_path*.

    For files inside the workspace the folder name is derived from the
    workspace-relative path (current behaviour).  For files **outside** the
    workspace a deterministic hash-based name is used so that reopening the
    same external file always resolves to the same directory.

    Example (internal)::

        workspace / .revisions / docs_plans_my-plan_md /

    Example (external)::

        workspace / .revisions / my-plan_a3f1c9b2 /
    """
    resolved = (workspace / file_path).resolve()
    try:
        rel = str(resolved.relative_to(workspace))
        # File is inside the workspace — use normalised relative path
        folder_name = normalize_path(rel)
    except ValueError:
        # File is outside the workspace — use deterministic hash
        folder_name = external_folder_name(str(resolved))
    return workspace / revisions_dir / folder_name


def _load_revisions_file(revisions_json: Path) -> dict[str, Any]:
    """Parse a ``revisions.json`` file."""
    return json.loads(revisions_json.read_text(encoding="utf-8"))


def _load_latest_annotations(
    plans_dir: Path, revisions_data: dict[str, Any]
) -> list[dict[str, Any]]:
    """Load the annotation array from the *latest* revision."""
    revisions = revisions_data.get("revisions", [])
    if not revisions:
        return []
    latest = revisions[-1]
    annotations_path = plans_dir / latest["annotationsFile"]
    if not annotations_path.exists():
        return []
    return json.loads(annotations_path.read_text(encoding="utf-8"))


def _save_latest_annotations(
    plans_dir: Path,
    revisions_data: dict[str, Any],
    annotations: list[dict[str, Any]],
) -> None:
    """Write the annotation array back to the latest revision's JSON file."""
    revisions = revisions_data.get("revisions", [])
    if not revisions:
        raise ValueError("No revisions exist — cannot save annotations")
    latest = revisions[-1]
    annotations_path = plans_dir / latest["annotationsFile"]
    annotations_path.write_text(
        json.dumps(annotations, indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def list_reviewed_files(
    workspace: Path, revisions_dir: str
) -> list[dict[str, Any]]:
    """Scan ``.revisions/`` and return summary info for every reviewed file."""
    root = workspace / revisions_dir
    if not root.exists():
        return []

    results: list[dict[str, Any]] = []

    for revisions_json in root.rglob("revisions.json"):
        try:
            plans_dir = revisions_json.parent
            data = _load_revisions_file(revisions_json)
            revisions = data.get("revisions", [])
            if not revisions:
                continue

            source_file: str = data.get("sourceFile", "").replace("\\", "/")
            latest = revisions[-1]

            # Load latest annotations for counts
            annotations = _load_latest_annotations(plans_dir, data)
            total = len(annotations)
            open_count = sum(
                1 for a in annotations if a.get("status") == "open"
            )

            results.append(
                {
                    "file_path": source_file,
                    "revision_count": len(revisions),
                    "total_annotations": total,
                    "open_count": open_count,
                    "last_review_date": latest.get("createdAt", ""),
                }
            )
        except Exception:
            # Skip malformed entries
            continue

    return results


def get_review_summary(
    workspace: Path, revisions_dir: str, file_path: str
) -> dict[str, Any]:
    """Return metadata for a file's review without full annotation payload."""
    plans_dir = _get_file_revisions_dir(workspace, revisions_dir, file_path)
    revisions_json = plans_dir / "revisions.json"
    if not revisions_json.exists():
        raise FileNotFoundError(
            f"No reviews found for '{file_path}'. "
            f"Expected revisions.json at: {revisions_json}"
        )

    data = _load_revisions_file(revisions_json)
    revisions = data.get("revisions", [])
    if not revisions:
        raise FileNotFoundError(f"No revisions found for '{file_path}'")

    latest = revisions[-1]
    annotations = _load_latest_annotations(plans_dir, data)

    counts: dict[str, int] = {"open": 0, "in_progress": 0, "resolved": 0, "wont_fix": 0}
    for a in annotations:
        status = a.get("status", "open")
        key = status.replace("-", "_")
        if key in counts:
            counts[key] += 1

    return {
        "file_path": file_path,
        "revision_count": len(revisions),
        "latest_revision": latest.get("revision", len(revisions) - 1),
        "counts": counts,
        "last_review_date": latest.get("createdAt", ""),
    }


def get_annotations(
    workspace: Path, revisions_dir: str, file_path: str
) -> list[dict[str, Any]]:
    """Return the full annotation array from the latest revision."""
    plans_dir = _get_file_revisions_dir(workspace, revisions_dir, file_path)
    revisions_json = plans_dir / "revisions.json"
    if not revisions_json.exists():
        raise FileNotFoundError(f"No reviews found for '{file_path}'")

    data = _load_revisions_file(revisions_json)
    return _load_latest_annotations(plans_dir, data)


def update_annotations(
    workspace: Path,
    revisions_dir: str,
    file_path: str,
    annotation_ids: list[str],
    status: Optional[str] = None,
    message: Optional[str] = None,
) -> int:
    """Update status and/or add an agent reply to matching annotations.

    Returns the number of annotations actually updated.
    """
    if not status and not message:
        raise ValueError("At least one of 'status' or 'message' must be provided")

    if status and status not in VALID_STATUSES:
        raise ValueError(
            f"Invalid status '{status}'. Must be one of: {', '.join(sorted(VALID_STATUSES))}"
        )

    plans_dir = _get_file_revisions_dir(workspace, revisions_dir, file_path)
    revisions_json = plans_dir / "revisions.json"
    if not revisions_json.exists():
        raise FileNotFoundError(f"No reviews found for '{file_path}'")

    data = _load_revisions_file(revisions_json)
    annotations = _load_latest_annotations(plans_dir, data)

    ids_set = set(annotation_ids)
    updated = 0

    for ann in annotations:
        if ann.get("id") not in ids_set:
            continue

        if status:
            ann["status"] = status

        if message:
            thread: list[dict[str, Any]] = ann.setdefault("thread", [])
            thread.append(
                {
                    "id": generate_id(),
                    "text": f"[AGENT] {message}",
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                }
            )

        updated += 1

    if updated > 0:
        _save_latest_annotations(plans_dir, data, annotations)

    return updated


def create_annotation(
    workspace: Path,
    revisions_dir: str,
    file_path: str,
    line: int,
    message: str,
    priority: str = "none",
    status: str = "open",
) -> dict[str, Any]:
    """Create a new annotation on a specific line.

    Returns the created annotation dict (including its generated ``id``).
    """
    if priority not in VALID_PRIORITIES:
        raise ValueError(
            f"Invalid priority '{priority}'. Must be one of: {', '.join(sorted(VALID_PRIORITIES))}"
        )
    if status not in VALID_STATUSES:
        raise ValueError(
            f"Invalid status '{status}'. Must be one of: {', '.join(sorted(VALID_STATUSES))}"
        )

    plans_dir = _get_file_revisions_dir(workspace, revisions_dir, file_path)
    revisions_json = plans_dir / "revisions.json"
    if not revisions_json.exists():
        raise FileNotFoundError(f"No reviews found for '{file_path}'")

    data = _load_revisions_file(revisions_json)
    annotations = _load_latest_annotations(plans_dir, data)

    # Read the snapshot to get a text preview for the line
    revisions = data.get("revisions", [])
    latest = revisions[-1]
    snapshot_path = plans_dir / latest["snapshotFile"]
    text_preview = ""
    if snapshot_path.exists():
        lines = snapshot_path.read_text(encoding="utf-8").splitlines()
        if 1 <= line <= len(lines):
            text_preview = lines[line - 1].strip()[:120]

    annotation: dict[str, Any] = {
        "id": generate_id(),
        "startLine": line,
        "endLine": line,
        "textPreview": text_preview,
        "priority": priority,
        "status": status,
        "thread": [
            {
                "id": generate_id(),
                "text": f"[AGENT] {message}",
                "createdAt": datetime.now(timezone.utc).isoformat(),
            }
        ],
    }

    annotations.append(annotation)
    # Keep sorted by startLine (matches extension behavior)
    annotations.sort(key=lambda a: a.get("startLine", 0))

    _save_latest_annotations(plans_dir, data, annotations)

    return annotation

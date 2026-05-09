"""JSON-based persistence for synthetic-panel."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Panel, Participant, ParticipantVersion, SessionLog, StudyAssignment

# ---------------------------------------------------------------------------
# Deserialisation helpers
# ---------------------------------------------------------------------------

def _participant_from_dict(d: dict[str, Any]) -> Participant:
    versions = [
        ParticipantVersion(
            version=v["version"],
            snapshot=v["snapshot"],
            created_at=v["created_at"],
            note=v.get("note", ""),
        )
        for v in d.get("versions", [])
    ]
    return Participant(
        id=d["id"],
        name=d["name"],
        archetype=d["archetype"],
        segment=d["segment"],
        attributes=d.get("attributes", {}),
        versions=versions,
        created_at=d["created_at"],
        updated_at=d["updated_at"],
        tags=d.get("tags", []),
    )


def _assignment_from_dict(d: dict[str, Any]) -> StudyAssignment:
    return StudyAssignment(
        id=d["id"],
        study_id=d["study_id"],
        study_name=d["study_name"],
        participant_id=d["participant_id"],
        participant_version=d["participant_version"],
        assigned_at=d["assigned_at"],
        notes=d.get("notes", ""),
    )


def _session_from_dict(d: dict[str, Any]) -> SessionLog:
    return SessionLog(
        id=d["id"],
        study_id=d["study_id"],
        participant_id=d["participant_id"],
        participant_version=d["participant_version"],
        session_date=d["session_date"],
        responses=d.get("responses", {}),
        notes=d.get("notes", ""),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def save_panel(panel: Panel, path: str | Path) -> None:
    """Persist a panel to a JSON file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(panel.to_dict(), fh, indent=2)


def load_panel(path: str | Path) -> Panel:
    """Load a panel from a JSON file."""
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    participants = {
        pid: _participant_from_dict(pdata)
        for pid, pdata in d.get("participants", {}).items()
    }
    assignments = [_assignment_from_dict(a) for a in d.get("assignments", [])]
    sessions = [_session_from_dict(s) for s in d.get("sessions", [])]
    return Panel(
        id=d["id"],
        name=d["name"],
        description=d.get("description", ""),
        participants=participants,
        assignments=assignments,
        sessions=sessions,
        created_at=d["created_at"],
        updated_at=d["updated_at"],
    )


def export_participants(panel: Panel, path: str | Path) -> None:
    """Export all participant records to a JSON array file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [p.to_dict() for p in panel.participants.values()]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def export_sessions(panel: Panel, path: str | Path) -> None:
    """Export all session logs to a JSON array file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [s.to_dict() for s in panel.sessions]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def export_assignments(panel: Panel, path: str | Path) -> None:
    """Export all study assignments to a JSON array file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [a.to_dict() for a in panel.assignments]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)

"""Core panel management operations for synthetic-panel."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from .models import (
    Panel,
    Participant,
    ParticipantVersion,
    SessionLog,
    StudyAssignment,
)


def _uid() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Panel lifecycle
# ---------------------------------------------------------------------------

def create_panel(name: str, description: str = "") -> Panel:
    """Create a new empty panel."""
    return Panel(
        id=_uid(),
        name=name,
        description=description,
        participants={},
        assignments=[],
        sessions=[],
        created_at=_now(),
        updated_at=_now(),
    )


# ---------------------------------------------------------------------------
# Participant management
# ---------------------------------------------------------------------------

def add_participant(
    panel: Panel,
    name: str,
    archetype: str,
    segment: str,
    attributes: dict[str, Any],
    tags: list[str] | None = None,
    note: str = "Initial version",
) -> Participant:
    """Add a new participant and record version 1."""
    pid = _uid()
    now = _now()
    tag_list = tags or []
    initial_snapshot: dict[str, Any] = {
        "name": name,
        "archetype": archetype,
        "segment": segment,
        "attributes": attributes,
        "tags": tag_list,
    }
    v1 = ParticipantVersion(version=1, snapshot=initial_snapshot, created_at=now, note=note)
    participant = Participant(
        id=pid,
        name=name,
        archetype=archetype,
        segment=segment,
        attributes=attributes,
        versions=[v1],
        created_at=now,
        updated_at=now,
        tags=tag_list,
    )
    panel.participants[pid] = participant
    panel.updated_at = now
    return participant


def update_participant(
    panel: Panel,
    participant_id: str,
    updates: dict[str, Any],
    note: str = "",
) -> Participant:
    """Update participant fields and snapshot a new version."""
    participant = panel.participants[participant_id]
    now = _now()
    allowed = {"name", "archetype", "segment", "attributes", "tags"}
    for key, value in updates.items():
        if key in allowed:
            setattr(participant, key, value)
    participant.updated_at = now
    snapshot: dict[str, Any] = {
        "name": participant.name,
        "archetype": participant.archetype,
        "segment": participant.segment,
        "attributes": participant.attributes,
        "tags": participant.tags,
    }
    new_ver = ParticipantVersion(
        version=len(participant.versions) + 1,
        snapshot=snapshot,
        created_at=now,
        note=note,
    )
    participant.versions.append(new_ver)
    panel.updated_at = now
    return participant


def remove_participant(panel: Panel, participant_id: str) -> bool:
    """Remove a participant from the panel. Returns True if found."""
    if participant_id not in panel.participants:
        return False
    del panel.participants[participant_id]
    panel.updated_at = _now()
    return True


def resolve_participant_id(panel: Panel, id_or_prefix: str) -> str | None:
    """Resolve a full ID or unambiguous prefix to a full participant ID."""
    if id_or_prefix in panel.participants:
        return id_or_prefix
    matches = [pid for pid in panel.participants if pid.startswith(id_or_prefix)]
    if len(matches) == 1:
        return matches[0]
    return None


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def filter_participants(
    panel: Panel,
    archetype: str | None = None,
    segment: str | None = None,
    tags: list[str] | None = None,
) -> list[Participant]:
    """Filter participants by archetype, segment, and/or tags."""
    results = list(panel.participants.values())
    if archetype:
        results = [p for p in results if p.archetype.lower() == archetype.lower()]
    if segment:
        results = [p for p in results if p.segment.lower() == segment.lower()]
    if tags:
        results = [p for p in results if any(t in p.tags for t in tags)]
    return results


# ---------------------------------------------------------------------------
# Study assignment
# ---------------------------------------------------------------------------

def assign_to_study(
    panel: Panel,
    study_id: str,
    study_name: str,
    participant_ids: list[str],
    notes: str = "",
) -> list[StudyAssignment]:
    """Assign a list of participants to a study at their current version."""
    now = _now()
    created: list[StudyAssignment] = []
    for pid in participant_ids:
        participant = panel.participants[pid]
        assignment = StudyAssignment(
            id=_uid(),
            study_id=study_id,
            study_name=study_name,
            participant_id=pid,
            participant_version=participant.current_version,
            assigned_at=now,
            notes=notes,
        )
        panel.assignments.append(assignment)
        created.append(assignment)
    panel.updated_at = now
    return created


def get_study_assignments(panel: Panel, study_id: str) -> list[StudyAssignment]:
    """Return all assignments for a given study."""
    return [a for a in panel.assignments if a.study_id == study_id]


# ---------------------------------------------------------------------------
# Session logging
# ---------------------------------------------------------------------------

def log_session(
    panel: Panel,
    study_id: str,
    participant_id: str,
    responses: dict[str, Any],
    notes: str = "",
    session_date: str | None = None,
) -> SessionLog:
    """Log a session response for a participant at their current version."""
    now = _now()
    participant = panel.participants[participant_id]
    session = SessionLog(
        id=_uid(),
        study_id=study_id,
        participant_id=participant_id,
        participant_version=participant.current_version,
        session_date=session_date or now,
        responses=responses,
        notes=notes,
    )
    panel.sessions.append(session)
    panel.updated_at = now
    return session


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def get_participant_history(panel: Panel, participant_id: str) -> dict[str, Any]:
    """Return full cross-study history for a single participant."""
    participant = panel.participants[participant_id]
    assignments = [a for a in panel.assignments if a.participant_id == participant_id]
    sessions = [s for s in panel.sessions if s.participant_id == participant_id]
    study_ids = {a.study_id for a in assignments}
    return {
        "participant": participant.to_dict(),
        "version_count": participant.current_version,
        "study_count": len(study_ids),
        "session_count": len(sessions),
        "assignments": [a.to_dict() for a in assignments],
        "sessions": [s.to_dict() for s in sessions],
    }


def panel_summary(panel: Panel) -> dict[str, Any]:
    """Return aggregate statistics about the panel."""
    archetypes: dict[str, int] = {}
    segments: dict[str, int] = {}
    for p in panel.participants.values():
        archetypes[p.archetype] = archetypes.get(p.archetype, 0) + 1
        segments[p.segment] = segments.get(p.segment, 0) + 1
    studies: dict[str, str] = {a.study_id: a.study_name for a in panel.assignments}
    return {
        "panel_id": panel.id,
        "panel_name": panel.name,
        "description": panel.description,
        "participant_count": len(panel.participants),
        "study_count": len(studies),
        "session_count": len(panel.sessions),
        "assignment_count": len(panel.assignments),
        "archetypes": archetypes,
        "segments": segments,
        "studies": studies,
    }


def compare_participant_versions(
    panel: Panel,
    participant_id: str,
    version_a: int,
    version_b: int,
) -> dict[str, Any]:
    """Compare two snapshots of a participant and return field-level diffs."""
    participant = panel.participants[participant_id]
    versions = {v.version: v for v in participant.versions}
    va = versions.get(version_a)
    vb = versions.get(version_b)
    if va is None or vb is None:
        return {"error": "One or both versions not found"}
    diffs: dict[str, Any] = {}
    all_keys = set(va.snapshot) | set(vb.snapshot)
    for key in all_keys:
        val_a = va.snapshot.get(key)
        val_b = vb.snapshot.get(key)
        if val_a != val_b:
            diffs[key] = {"v{version_a}": val_a, f"v{version_b}": val_b}
    return {
        "participant_id": participant_id,
        "participant_name": participant.name,
        "version_a": version_a,
        "version_b": version_b,
        "changed_fields": list(diffs.keys()),
        "diffs": diffs,
    }

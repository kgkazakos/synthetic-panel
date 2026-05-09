"""Data models for synthetic-panel."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _uid() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ParticipantVersion:
    version: int
    snapshot: dict[str, Any]
    created_at: str
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "snapshot": self.snapshot,
            "created_at": self.created_at,
            "note": self.note,
        }


@dataclass
class Participant:
    id: str
    name: str
    archetype: str
    segment: str
    attributes: dict[str, Any]
    versions: list[ParticipantVersion]
    created_at: str
    updated_at: str
    tags: list[str] = field(default_factory=list)

    @property
    def current_version(self) -> int:
        return len(self.versions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "archetype": self.archetype,
            "segment": self.segment,
            "attributes": self.attributes,
            "versions": [v.to_dict() for v in self.versions],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": self.tags,
        }


@dataclass
class StudyAssignment:
    id: str
    study_id: str
    study_name: str
    participant_id: str
    participant_version: int
    assigned_at: str
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "study_id": self.study_id,
            "study_name": self.study_name,
            "participant_id": self.participant_id,
            "participant_version": self.participant_version,
            "assigned_at": self.assigned_at,
            "notes": self.notes,
        }


@dataclass
class SessionLog:
    id: str
    study_id: str
    participant_id: str
    participant_version: int
    session_date: str
    responses: dict[str, Any]
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "study_id": self.study_id,
            "participant_id": self.participant_id,
            "participant_version": self.participant_version,
            "session_date": self.session_date,
            "responses": self.responses,
            "notes": self.notes,
        }


@dataclass
class Panel:
    id: str
    name: str
    description: str
    participants: dict[str, Participant]
    assignments: list[StudyAssignment]
    sessions: list[SessionLog]
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "participants": {pid: p.to_dict() for pid, p in self.participants.items()},
            "assignments": [a.to_dict() for a in self.assignments],
            "sessions": [s.to_dict() for s in self.sessions],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

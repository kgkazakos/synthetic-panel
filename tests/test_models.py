"""Tests for synthetic_panel.models."""
import pytest
from synthetic_panel.models import (
    Panel,
    Participant,
    ParticipantVersion,
    SessionLog,
    StudyAssignment,
)


# ---------------------------------------------------------------------------
# ParticipantVersion
# ---------------------------------------------------------------------------

class TestParticipantVersion:
    def test_to_dict_basic(self):
        v = ParticipantVersion(
            version=1,
            snapshot={"name": "Alex", "archetype": "Power User"},
            created_at="2026-04-01T09:00:00+00:00",
            note="Initial version",
        )
        d = v.to_dict()
        assert d["version"] == 1
        assert d["snapshot"]["name"] == "Alex"
        assert d["note"] == "Initial version"

    def test_to_dict_empty_note(self):
        v = ParticipantVersion(version=2, snapshot={}, created_at="2026-04-01", note="")
        assert v.to_dict()["note"] == ""

    def test_snapshot_preserved(self):
        snap = {"a": 1, "b": [1, 2, 3]}
        v = ParticipantVersion(version=1, snapshot=snap, created_at="2026-04-01")
        assert v.to_dict()["snapshot"] == snap


# ---------------------------------------------------------------------------
# Participant
# ---------------------------------------------------------------------------

class TestParticipant:
    def _make(self, n_versions: int = 1) -> Participant:
        versions = [
            ParticipantVersion(version=i, snapshot={}, created_at="2026-04-01")
            for i in range(1, n_versions + 1)
        ]
        return Participant(
            id="part-001",
            name="Alex",
            archetype="Power User",
            segment="Young Professional",
            attributes={"tech_comfort": "high"},
            versions=versions,
            created_at="2026-04-01",
            updated_at="2026-04-01",
            tags=["digital-native"],
        )

    def test_current_version_single(self):
        p = self._make(1)
        assert p.current_version == 1

    def test_current_version_multiple(self):
        p = self._make(3)
        assert p.current_version == 3

    def test_to_dict_structure(self):
        p = self._make(2)
        d = p.to_dict()
        assert d["id"] == "part-001"
        assert d["name"] == "Alex"
        assert d["archetype"] == "Power User"
        assert d["segment"] == "Young Professional"
        assert d["attributes"] == {"tech_comfort": "high"}
        assert len(d["versions"]) == 2
        assert d["tags"] == ["digital-native"]

    def test_to_dict_empty_tags(self):
        p = self._make(1)
        p.tags = []
        assert p.to_dict()["tags"] == []

    def test_to_dict_versions_serialised(self):
        p = self._make(2)
        d = p.to_dict()
        assert d["versions"][0]["version"] == 1
        assert d["versions"][1]["version"] == 2


# ---------------------------------------------------------------------------
# StudyAssignment
# ---------------------------------------------------------------------------

class TestStudyAssignment:
    def test_to_dict(self):
        a = StudyAssignment(
            id="assign-001",
            study_id="study-01",
            study_name="Wave 1",
            participant_id="part-001",
            participant_version=2,
            assigned_at="2026-04-05T09:00:00+00:00",
            notes="test note",
        )
        d = a.to_dict()
        assert d["study_id"] == "study-01"
        assert d["participant_version"] == 2
        assert d["notes"] == "test note"

    def test_to_dict_empty_notes(self):
        a = StudyAssignment(
            id="a",
            study_id="s",
            study_name="n",
            participant_id="p",
            participant_version=1,
            assigned_at="2026-04-01",
        )
        assert a.to_dict()["notes"] == ""


# ---------------------------------------------------------------------------
# SessionLog
# ---------------------------------------------------------------------------

class TestSessionLog:
    def test_to_dict(self):
        s = SessionLog(
            id="sess-001",
            study_id="study-01",
            participant_id="part-001",
            participant_version=1,
            session_date="2026-04-06T10:00:00+00:00",
            responses={"sus_score": 72, "completed": True},
            notes="Great session",
        )
        d = s.to_dict()
        assert d["responses"]["sus_score"] == 72
        assert d["participant_version"] == 1
        assert d["notes"] == "Great session"

    def test_to_dict_empty_responses(self):
        s = SessionLog(
            id="s", study_id="st", participant_id="p",
            participant_version=1, session_date="2026-04-01", responses={},
        )
        assert s.to_dict()["responses"] == {}


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------

class TestPanel:
    def _make_panel(self) -> Panel:
        return Panel(
            id="panel-001",
            name="Test Panel",
            description="For testing",
            participants={},
            assignments=[],
            sessions=[],
            created_at="2026-04-01",
            updated_at="2026-04-01",
        )

    def test_to_dict_empty(self):
        p = self._make_panel()
        d = p.to_dict()
        assert d["name"] == "Test Panel"
        assert d["participants"] == {}
        assert d["assignments"] == []
        assert d["sessions"] == []

    def test_to_dict_with_participants(self):
        p = self._make_panel()
        v = ParticipantVersion(version=1, snapshot={}, created_at="2026-04-01")
        pt = Participant(
            id="part-x",
            name="X",
            archetype="A",
            segment="S",
            attributes={},
            versions=[v],
            created_at="2026-04-01",
            updated_at="2026-04-01",
        )
        p.participants["part-x"] = pt
        d = p.to_dict()
        assert "part-x" in d["participants"]
        assert d["participants"]["part-x"]["name"] == "X"

"""Tests for synthetic_panel.storage — persistence round-trips."""
import json
from pathlib import Path

import pytest

from synthetic_panel.models import Panel
from synthetic_panel.panel import (
    add_participant,
    assign_to_study,
    create_panel,
    log_session,
    update_participant,
)
from synthetic_panel.storage import (
    export_assignments,
    export_participants,
    export_sessions,
    load_panel,
    save_panel,
)

FIXTURE = Path(__file__).parent / "fixtures" / "sample_panel.json"


# ---------------------------------------------------------------------------
# Fixture loading
# ---------------------------------------------------------------------------

class TestLoadFixture:
    def test_loads_without_error(self):
        panel = load_panel(FIXTURE)
        assert panel is not None

    def test_participant_count(self):
        panel = load_panel(FIXTURE)
        assert len(panel.participants) == 3

    def test_participant_names(self):
        panel = load_panel(FIXTURE)
        names = {p.name for p in panel.participants.values()}
        assert "Alex Chen" in names
        assert "Maria Santos" in names
        assert "James Okafor" in names

    def test_multi_version_participant(self):
        panel = load_panel(FIXTURE)
        alex = next(p for p in panel.participants.values() if p.name == "Alex Chen")
        assert alex.current_version == 2

    def test_assignments_loaded(self):
        panel = load_panel(FIXTURE)
        assert len(panel.assignments) == 3

    def test_sessions_loaded(self):
        panel = load_panel(FIXTURE)
        assert len(panel.sessions) == 3

    def test_panel_name(self):
        panel = load_panel(FIXTURE)
        assert panel.name == "Mobile Banking Study Panel"

    def test_tags_preserved(self):
        panel = load_panel(FIXTURE)
        alex = next(p for p in panel.participants.values() if p.name == "Alex Chen")
        assert "digital-native" in alex.tags
        assert "crypto-curious" in alex.tags

    def test_responses_preserved(self):
        panel = load_panel(FIXTURE)
        session = panel.sessions[0]
        assert "sus_score" in session.responses
        assert session.responses["sus_score"] == 72


# ---------------------------------------------------------------------------
# Save / load round-trip
# ---------------------------------------------------------------------------

class TestSaveLoadRoundTrip:
    def test_basic_round_trip(self, tmp_path: Path):
        p = create_panel("Round Trip Panel", "desc")
        add_participant(p, "Alice", "Explorer", "Early Adopter", {"x": 1}, tags=["t1"])
        path = tmp_path / "panel.json"
        save_panel(p, path)
        loaded = load_panel(path)
        assert loaded.name == "Round Trip Panel"
        assert len(loaded.participants) == 1

    def test_participant_fields_preserved(self, tmp_path: Path):
        p = create_panel("RT")
        add_participant(
            p, "Bob", "Doubter", "Mid-market",
            {"comfort": "low", "scores": [1, 2, 3]},
            tags=["risk-averse"],
        )
        path = tmp_path / "panel.json"
        save_panel(p, path)
        loaded = load_panel(path)
        pt = list(loaded.participants.values())[0]
        assert pt.name == "Bob"
        assert pt.archetype == "Doubter"
        assert pt.attributes["comfort"] == "low"
        assert pt.attributes["scores"] == [1, 2, 3]
        assert "risk-averse" in pt.tags

    def test_versions_preserved(self, tmp_path: Path):
        p = create_panel("Ver RT")
        part = add_participant(p, "Carol", "Arch", "Seg", {})
        update_participant(p, part.id, {"archetype": "New Arch"}, note="Evolved")
        path = tmp_path / "panel.json"
        save_panel(p, path)
        loaded = load_panel(path)
        pt = list(loaded.participants.values())[0]
        assert pt.current_version == 2
        assert pt.versions[0].note == "Initial version"
        assert pt.versions[1].note == "Evolved"

    def test_assignments_preserved(self, tmp_path: Path):
        p = create_panel("Assign RT")
        part = add_participant(p, "Dave", "A", "S", {})
        assign_to_study(p, "study-x", "Study X", [part.id], notes="note")
        path = tmp_path / "panel.json"
        save_panel(p, path)
        loaded = load_panel(path)
        assert len(loaded.assignments) == 1
        a = loaded.assignments[0]
        assert a.study_id == "study-x"
        assert a.study_name == "Study X"
        assert a.notes == "note"

    def test_sessions_preserved(self, tmp_path: Path):
        p = create_panel("Sess RT")
        part = add_participant(p, "Eve", "A", "S", {})
        log_session(p, "study-y", part.id, {"score": 88}, notes="Good")
        path = tmp_path / "panel.json"
        save_panel(p, path)
        loaded = load_panel(path)
        assert len(loaded.sessions) == 1
        s = loaded.sessions[0]
        assert s.responses["score"] == 88
        assert s.notes == "Good"

    def test_multiple_participants_round_trip(self, tmp_path: Path):
        p = create_panel("Multi RT")
        for i in range(5):
            add_participant(p, f"User {i}", "Arch", "Seg", {"i": i})
        path = tmp_path / "panel.json"
        save_panel(p, path)
        loaded = load_panel(path)
        assert len(loaded.participants) == 5

    def test_file_is_valid_json(self, tmp_path: Path):
        p = create_panel("JSON Check")
        add_participant(p, "Frank", "A", "S", {})
        path = tmp_path / "panel.json"
        save_panel(p, path)
        with open(path) as f:
            data = json.load(f)
        assert "participants" in data
        assert "assignments" in data


# ---------------------------------------------------------------------------
# Export functions
# ---------------------------------------------------------------------------

class TestExportParticipants:
    def test_creates_file(self, tmp_path: Path):
        p = create_panel("Export")
        add_participant(p, "Grace", "A", "S", {})
        dest = tmp_path / "participants.json"
        export_participants(p, dest)
        assert dest.exists()

    def test_file_is_array(self, tmp_path: Path):
        p = create_panel("Export")
        add_participant(p, "Grace", "A", "S", {})
        dest = tmp_path / "participants.json"
        export_participants(p, dest)
        with open(dest) as f:
            data = json.load(f)
        assert isinstance(data, list)

    def test_count_matches(self, tmp_path: Path):
        p = create_panel("Export")
        add_participant(p, "Grace", "A", "S", {})
        add_participant(p, "Henry", "B", "T", {})
        dest = tmp_path / "participants.json"
        export_participants(p, dest)
        with open(dest) as f:
            data = json.load(f)
        assert len(data) == 2

    def test_empty_panel(self, tmp_path: Path):
        p = create_panel("Empty")
        dest = tmp_path / "participants.json"
        export_participants(p, dest)
        with open(dest) as f:
            data = json.load(f)
        assert data == []


class TestExportSessions:
    def test_creates_file(self, tmp_path: Path):
        p = create_panel("Export")
        part = add_participant(p, "Ivy", "A", "S", {})
        log_session(p, "study-01", part.id, {"q": 1})
        dest = tmp_path / "sessions.json"
        export_sessions(p, dest)
        assert dest.exists()

    def test_file_is_array(self, tmp_path: Path):
        p = create_panel("Export")
        part = add_participant(p, "Ivy", "A", "S", {})
        log_session(p, "study-01", part.id, {"q": 1})
        dest = tmp_path / "sessions.json"
        export_sessions(p, dest)
        with open(dest) as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) == 1

    def test_responses_preserved(self, tmp_path: Path):
        p = create_panel("Export")
        part = add_participant(p, "Jack", "A", "S", {})
        log_session(p, "study-01", part.id, {"sus_score": 90})
        dest = tmp_path / "sessions.json"
        export_sessions(p, dest)
        with open(dest) as f:
            data = json.load(f)
        assert data[0]["responses"]["sus_score"] == 90


class TestExportAssignments:
    def test_creates_file(self, tmp_path: Path):
        p = create_panel("Export")
        part = add_participant(p, "Kate", "A", "S", {})
        assign_to_study(p, "study-01", "Study 1", [part.id])
        dest = tmp_path / "assignments.json"
        export_assignments(p, dest)
        assert dest.exists()

    def test_file_is_array(self, tmp_path: Path):
        p = create_panel("Export")
        part = add_participant(p, "Leo", "A", "S", {})
        assign_to_study(p, "study-01", "Study 1", [part.id])
        dest = tmp_path / "assignments.json"
        export_assignments(p, dest)
        with open(dest) as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) == 1

    def test_empty_assignments(self, tmp_path: Path):
        p = create_panel("Empty")
        dest = tmp_path / "assignments.json"
        export_assignments(p, dest)
        with open(dest) as f:
            data = json.load(f)
        assert data == []


# ---------------------------------------------------------------------------
# Directory creation
# ---------------------------------------------------------------------------

class TestDirectoryCreation:
    def test_creates_parent_dirs(self, tmp_path: Path):
        p = create_panel("Dir Test")
        nested = tmp_path / "a" / "b" / "c" / "panel.json"
        save_panel(p, nested)
        assert nested.exists()

    def test_export_creates_parent_dirs(self, tmp_path: Path):
        p = create_panel("Dir Test")
        nested = tmp_path / "exports" / "sub" / "participants.json"
        export_participants(p, nested)
        assert nested.exists()

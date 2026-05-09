"""Tests for synthetic_panel.panel — core operations."""
import pytest
from synthetic_panel.panel import (
    add_participant,
    assign_to_study,
    compare_participant_versions,
    create_panel,
    filter_participants,
    get_participant_history,
    get_study_assignments,
    log_session,
    panel_summary,
    remove_participant,
    resolve_participant_id,
    update_participant,
)
from synthetic_panel.models import Panel


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def empty_panel() -> Panel:
    return create_panel("Test Panel", "For unit tests")


@pytest.fixture()
def panel_with_participants() -> Panel:
    p = create_panel("Banking Panel")
    add_participant(
        p, "Alex Chen", "Power User", "Young Professional",
        {"tech_comfort": "high", "device": "iOS"},
        tags=["digital-native", "high-value"],
        note="Initial version",
    )
    add_participant(
        p, "Maria Santos", "Cautious Saver", "Mid-career",
        {"tech_comfort": "medium", "device": "Android"},
        tags=["savings-focused"],
        note="Initial version",
    )
    add_participant(
        p, "James Okafor", "Reluctant Adopter", "Near Retirement",
        {"tech_comfort": "low", "device": "Android"},
        tags=["accessibility-needs"],
        note="Initial version",
    )
    return p


# ---------------------------------------------------------------------------
# create_panel
# ---------------------------------------------------------------------------

class TestCreatePanel:
    def test_basic_fields(self):
        p = create_panel("My Panel", "desc")
        assert p.name == "My Panel"
        assert p.description == "desc"
        assert p.participants == {}
        assert p.assignments == []
        assert p.sessions == []

    def test_unique_ids(self):
        p1 = create_panel("A")
        p2 = create_panel("B")
        assert p1.id != p2.id

    def test_empty_description_default(self):
        p = create_panel("No Desc")
        assert p.description == ""


# ---------------------------------------------------------------------------
# add_participant
# ---------------------------------------------------------------------------

class TestAddParticipant:
    def test_adds_to_panel(self, empty_panel: Panel):
        add_participant(empty_panel, "Alex", "Power User", "YP", {})
        assert len(empty_panel.participants) == 1

    def test_version_1_created(self, empty_panel: Panel):
        p = add_participant(empty_panel, "Alex", "Power User", "YP", {})
        assert p.current_version == 1
        assert len(p.versions) == 1

    def test_version_note_stored(self, empty_panel: Panel):
        p = add_participant(empty_panel, "Alex", "Power User", "YP", {}, note="First draft")
        assert p.versions[0].note == "First draft"

    def test_tags_stored(self, empty_panel: Panel):
        p = add_participant(empty_panel, "Alex", "Power User", "YP", {}, tags=["a", "b"])
        assert "a" in p.tags
        assert "b" in p.tags

    def test_attributes_preserved(self, empty_panel: Panel):
        attrs = {"tech_comfort": "high", "age_range": "25-34"}
        p = add_participant(empty_panel, "Alex", "Power User", "YP", attrs)
        assert p.attributes == attrs

    def test_no_tags_default(self, empty_panel: Panel):
        p = add_participant(empty_panel, "Alex", "Power User", "YP", {})
        assert p.tags == []

    def test_panel_updated_at_changes(self, empty_panel: Panel):
        before = empty_panel.updated_at
        add_participant(empty_panel, "Alex", "Power User", "YP", {})
        assert empty_panel.updated_at >= before

    def test_snapshot_stored_in_v1(self, empty_panel: Panel):
        p = add_participant(
            empty_panel, "Alex", "Power User", "YP",
            {"x": 1}, tags=["t1"],
        )
        snap = p.versions[0].snapshot
        assert snap["name"] == "Alex"
        assert snap["archetype"] == "Power User"
        assert snap["attributes"] == {"x": 1}


# ---------------------------------------------------------------------------
# update_participant
# ---------------------------------------------------------------------------

class TestUpdateParticipant:
    def test_version_bumped(self, panel_with_participants: Panel):
        pid = list(panel_with_participants.participants.keys())[0]
        update_participant(panel_with_participants, pid, {"archetype": "Super User"})
        assert panel_with_participants.participants[pid].current_version == 2

    def test_field_updated(self, panel_with_participants: Panel):
        pid = list(panel_with_participants.participants.keys())[0]
        update_participant(panel_with_participants, pid, {"archetype": "Super User"})
        assert panel_with_participants.participants[pid].archetype == "Super User"

    def test_note_stored(self, panel_with_participants: Panel):
        pid = list(panel_with_participants.participants.keys())[0]
        update_participant(panel_with_participants, pid, {"segment": "Senior"}, note="Post wave 1")
        p = panel_with_participants.participants[pid]
        assert p.versions[-1].note == "Post wave 1"

    def test_original_version_preserved(self, panel_with_participants: Panel):
        pid = list(panel_with_participants.participants.keys())[0]
        original_archetype = panel_with_participants.participants[pid].versions[0].snapshot["archetype"]
        update_participant(panel_with_participants, pid, {"archetype": "Super User"})
        assert panel_with_participants.participants[pid].versions[0].snapshot["archetype"] == original_archetype

    def test_attributes_update(self, panel_with_participants: Panel):
        pid = list(panel_with_participants.participants.keys())[0]
        update_participant(panel_with_participants, pid, {"attributes": {"tech_comfort": "very_high"}})
        assert panel_with_participants.participants[pid].attributes["tech_comfort"] == "very_high"

    def test_tags_update(self, panel_with_participants: Panel):
        pid = list(panel_with_participants.participants.keys())[0]
        update_participant(panel_with_participants, pid, {"tags": ["new-tag"]})
        assert "new-tag" in panel_with_participants.participants[pid].tags

    def test_multiple_updates_increment_version(self, panel_with_participants: Panel):
        pid = list(panel_with_participants.participants.keys())[0]
        update_participant(panel_with_participants, pid, {"segment": "A"})
        update_participant(panel_with_participants, pid, {"segment": "B"})
        update_participant(panel_with_participants, pid, {"segment": "C"})
        assert panel_with_participants.participants[pid].current_version == 4


# ---------------------------------------------------------------------------
# remove_participant
# ---------------------------------------------------------------------------

class TestRemoveParticipant:
    def test_removes_existing(self, panel_with_participants: Panel):
        pid = list(panel_with_participants.participants.keys())[0]
        result = remove_participant(panel_with_participants, pid)
        assert result is True
        assert pid not in panel_with_participants.participants

    def test_returns_false_for_missing(self, panel_with_participants: Panel):
        result = remove_participant(panel_with_participants, "nonexistent-id")
        assert result is False

    def test_count_decreases(self, panel_with_participants: Panel):
        before = len(panel_with_participants.participants)
        pid = list(panel_with_participants.participants.keys())[0]
        remove_participant(panel_with_participants, pid)
        assert len(panel_with_participants.participants) == before - 1


# ---------------------------------------------------------------------------
# resolve_participant_id
# ---------------------------------------------------------------------------

class TestResolveParticipantId:
    def test_full_id_resolves(self, panel_with_participants: Panel):
        pid = list(panel_with_participants.participants.keys())[0]
        assert resolve_participant_id(panel_with_participants, pid) == pid

    def test_prefix_resolves(self, panel_with_participants: Panel):
        pid = list(panel_with_participants.participants.keys())[0]
        prefix = pid[:8]
        assert resolve_participant_id(panel_with_participants, prefix) == pid

    def test_ambiguous_prefix_returns_none(self, panel_with_participants: Panel):
        # All UUIDs start with different chars, so use a deliberately empty prefix
        # that would match everything — use a single common char hack isn't reliable
        # Instead add two participants with same prefix manually
        p = create_panel("Ambig")
        add_participant(p, "A", "X", "Y", {})
        add_participant(p, "B", "X", "Y", {})
        # Both IDs start with different chars; to force ambiguity use prefix ""
        result = resolve_participant_id(p, "")
        # "" is prefix of everything → ambiguous
        assert result is None

    def test_nonexistent_returns_none(self, panel_with_participants: Panel):
        assert resolve_participant_id(panel_with_participants, "zzz-does-not-exist") is None


# ---------------------------------------------------------------------------
# filter_participants
# ---------------------------------------------------------------------------

class TestFilterParticipants:
    def test_no_filters_returns_all(self, panel_with_participants: Panel):
        results = filter_participants(panel_with_participants)
        assert len(results) == 3

    def test_filter_by_archetype(self, panel_with_participants: Panel):
        results = filter_participants(panel_with_participants, archetype="Power User")
        assert len(results) == 1
        assert results[0].name == "Alex Chen"

    def test_filter_by_segment(self, panel_with_participants: Panel):
        results = filter_participants(panel_with_participants, segment="Mid-career")
        assert len(results) == 1
        assert results[0].name == "Maria Santos"

    def test_filter_by_tag(self, panel_with_participants: Panel):
        results = filter_participants(panel_with_participants, tags=["accessibility-needs"])
        assert len(results) == 1
        assert results[0].name == "James Okafor"

    def test_filter_case_insensitive_archetype(self, panel_with_participants: Panel):
        results = filter_participants(panel_with_participants, archetype="power user")
        assert len(results) == 1

    def test_filter_no_match(self, panel_with_participants: Panel):
        results = filter_participants(panel_with_participants, archetype="Ghost Archetype")
        assert results == []

    def test_filter_combined(self, panel_with_participants: Panel):
        results = filter_participants(
            panel_with_participants, archetype="Power User", segment="Young Professional"
        )
        assert len(results) == 1


# ---------------------------------------------------------------------------
# assign_to_study
# ---------------------------------------------------------------------------

class TestAssignToStudy:
    def test_creates_assignments(self, panel_with_participants: Panel):
        pids = list(panel_with_participants.participants.keys())[:2]
        assignments = assign_to_study(
            panel_with_participants, "study-01", "Wave 1", pids
        )
        assert len(assignments) == 2

    def test_stored_on_panel(self, panel_with_participants: Panel):
        pids = list(panel_with_participants.participants.keys())[:1]
        assign_to_study(panel_with_participants, "study-01", "Wave 1", pids)
        assert len(panel_with_participants.assignments) == 1

    def test_version_snapshotted(self, panel_with_participants: Panel):
        pid = list(panel_with_participants.participants.keys())[0]
        update_participant(panel_with_participants, pid, {"archetype": "Super User"})
        assignments = assign_to_study(panel_with_participants, "study-02", "Wave 2", [pid])
        assert assignments[0].participant_version == 2

    def test_notes_stored(self, panel_with_participants: Panel):
        pids = list(panel_with_participants.participants.keys())[:1]
        assignments = assign_to_study(
            panel_with_participants, "study-01", "Wave 1", pids, notes="Test note"
        )
        assert assignments[0].notes == "Test note"

    def test_get_study_assignments_filters(self, panel_with_participants: Panel):
        pids = list(panel_with_participants.participants.keys())
        assign_to_study(panel_with_participants, "study-01", "Wave 1", pids[:2])
        assign_to_study(panel_with_participants, "study-02", "Wave 2", pids[2:])
        s1 = get_study_assignments(panel_with_participants, "study-01")
        s2 = get_study_assignments(panel_with_participants, "study-02")
        assert len(s1) == 2
        assert len(s2) == 1

    def test_get_study_assignments_empty(self, panel_with_participants: Panel):
        result = get_study_assignments(panel_with_participants, "nonexistent")
        assert result == []


# ---------------------------------------------------------------------------
# log_session
# ---------------------------------------------------------------------------

class TestLogSession:
    def test_creates_session(self, panel_with_participants: Panel):
        pid = list(panel_with_participants.participants.keys())[0]
        session = log_session(
            panel_with_participants, "study-01", pid,
            {"sus_score": 72, "completed": True},
            notes="Smooth session",
        )
        assert session.study_id == "study-01"
        assert session.participant_id == pid
        assert session.responses["sus_score"] == 72

    def test_stored_on_panel(self, panel_with_participants: Panel):
        pid = list(panel_with_participants.participants.keys())[0]
        log_session(panel_with_participants, "study-01", pid, {})
        assert len(panel_with_participants.sessions) == 1

    def test_version_captured(self, panel_with_participants: Panel):
        pid = list(panel_with_participants.participants.keys())[0]
        update_participant(panel_with_participants, pid, {"archetype": "Super User"})
        session = log_session(panel_with_participants, "study-02", pid, {})
        assert session.participant_version == 2

    def test_custom_session_date(self, panel_with_participants: Panel):
        pid = list(panel_with_participants.participants.keys())[0]
        session = log_session(
            panel_with_participants, "study-01", pid, {},
            session_date="2026-04-06T10:00:00+00:00",
        )
        assert session.session_date == "2026-04-06T10:00:00+00:00"

    def test_empty_responses_allowed(self, panel_with_participants: Panel):
        pid = list(panel_with_participants.participants.keys())[0]
        session = log_session(panel_with_participants, "study-01", pid, {})
        assert session.responses == {}

    def test_multiple_sessions_accumulate(self, panel_with_participants: Panel):
        pid = list(panel_with_participants.participants.keys())[0]
        log_session(panel_with_participants, "study-01", pid, {"q": 1})
        log_session(panel_with_participants, "study-01", pid, {"q": 2})
        sessions = [s for s in panel_with_participants.sessions if s.participant_id == pid]
        assert len(sessions) == 2


# ---------------------------------------------------------------------------
# get_participant_history
# ---------------------------------------------------------------------------

class TestGetParticipantHistory:
    def _setup(self, panel_with_participants: Panel):
        pid = list(panel_with_participants.participants.keys())[0]
        assign_to_study(panel_with_participants, "study-01", "Wave 1", [pid])
        assign_to_study(panel_with_participants, "study-02", "Wave 2", [pid])
        log_session(panel_with_participants, "study-01", pid, {"sus": 70})
        log_session(panel_with_participants, "study-02", pid, {"sus": 80})
        return pid

    def test_study_count(self, panel_with_participants: Panel):
        pid = self._setup(panel_with_participants)
        history = get_participant_history(panel_with_participants, pid)
        assert history["study_count"] == 2

    def test_session_count(self, panel_with_participants: Panel):
        pid = self._setup(panel_with_participants)
        history = get_participant_history(panel_with_participants, pid)
        assert history["session_count"] == 2

    def test_version_count(self, panel_with_participants: Panel):
        pid = self._setup(panel_with_participants)
        update_participant(panel_with_participants, pid, {"archetype": "Super User"})
        history = get_participant_history(panel_with_participants, pid)
        assert history["version_count"] == 2

    def test_participant_in_history(self, panel_with_participants: Panel):
        pid = self._setup(panel_with_participants)
        history = get_participant_history(panel_with_participants, pid)
        assert history["participant"]["id"] == pid


# ---------------------------------------------------------------------------
# panel_summary
# ---------------------------------------------------------------------------

class TestPanelSummary:
    def test_participant_count(self, panel_with_participants: Panel):
        s = panel_summary(panel_with_participants)
        assert s["participant_count"] == 3

    def test_archetypes(self, panel_with_participants: Panel):
        s = panel_summary(panel_with_participants)
        assert "Power User" in s["archetypes"]
        assert s["archetypes"]["Power User"] == 1

    def test_segments(self, panel_with_participants: Panel):
        s = panel_summary(panel_with_participants)
        assert "Young Professional" in s["segments"]

    def test_study_count_zero(self, panel_with_participants: Panel):
        s = panel_summary(panel_with_participants)
        assert s["study_count"] == 0

    def test_study_count_after_assignment(self, panel_with_participants: Panel):
        pids = list(panel_with_participants.participants.keys())[:2]
        assign_to_study(panel_with_participants, "study-01", "Wave 1", pids)
        s = panel_summary(panel_with_participants)
        assert s["study_count"] == 1

    def test_session_count(self, panel_with_participants: Panel):
        pid = list(panel_with_participants.participants.keys())[0]
        log_session(panel_with_participants, "study-01", pid, {})
        log_session(panel_with_participants, "study-01", pid, {})
        s = panel_summary(panel_with_participants)
        assert s["session_count"] == 2

    def test_empty_panel(self, empty_panel: Panel):
        s = panel_summary(empty_panel)
        assert s["participant_count"] == 0
        assert s["study_count"] == 0
        assert s["session_count"] == 0


# ---------------------------------------------------------------------------
# compare_participant_versions
# ---------------------------------------------------------------------------

class TestCompareParticipantVersions:
    def test_no_diff_same_version_content(self, panel_with_participants: Panel):
        pid = list(panel_with_participants.participants.keys())[0]
        update_participant(panel_with_participants, pid, {})
        result = compare_participant_versions(panel_with_participants, pid, 1, 2)
        # No fields changed in the update dict, but snapshot is identical
        assert "changed_fields" in result

    def test_diff_detected(self, panel_with_participants: Panel):
        pid = list(panel_with_participants.participants.keys())[0]
        update_participant(panel_with_participants, pid, {"archetype": "Super User"}, note="Evolved")
        result = compare_participant_versions(panel_with_participants, pid, 1, 2)
        assert "archetype" in result["changed_fields"]

    def test_missing_version_returns_error(self, panel_with_participants: Panel):
        pid = list(panel_with_participants.participants.keys())[0]
        result = compare_participant_versions(panel_with_participants, pid, 1, 99)
        assert "error" in result

    def test_result_structure(self, panel_with_participants: Panel):
        pid = list(panel_with_participants.participants.keys())[0]
        update_participant(panel_with_participants, pid, {"segment": "Senior"})
        result = compare_participant_versions(panel_with_participants, pid, 1, 2)
        assert "participant_id" in result
        assert "participant_name" in result
        assert "changed_fields" in result
        assert "diffs" in result

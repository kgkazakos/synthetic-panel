"""Tests for synthetic_panel CLI — Click test runner."""
import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from synthetic_panel.cli import cli
from synthetic_panel.panel import add_participant, assign_to_study, create_panel, log_session
from synthetic_panel.storage import save_panel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture()
def runner():
    return CliRunner()


@pytest.fixture()
def panel_file(tmp_path: Path) -> Path:
    p = create_panel("CLI Test Panel", "For CLI tests")
    path = tmp_path / "panel.json"
    save_panel(p, path)
    return path


@pytest.fixture()
def populated_panel_file(tmp_path: Path) -> Path:
    p = create_panel("Populated Panel")
    add_participant(p, "Alice", "Power User", "Young Professional", {"x": 1}, tags=["tag-a"])
    add_participant(p, "Bob", "Cautious Saver", "Mid-career", {"y": 2}, tags=["tag-b"])
    path = tmp_path / "panel.json"
    save_panel(p, path)
    return path


def _get_first_pid(panel_file: Path) -> str:
    from synthetic_panel.storage import load_panel
    p = load_panel(panel_file)
    return list(p.participants.keys())[0]


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------

class TestInitCommand:
    def test_creates_file(self, runner: CliRunner, tmp_path: Path):
        out = tmp_path / "new_panel.json"
        result = runner.invoke(cli, ["init", "Test Panel", "--output", str(out)])
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_json_output(self, runner: CliRunner, tmp_path: Path):
        out = tmp_path / "new.json"
        result = runner.invoke(cli, ["init", "My Panel", "--output", str(out), "--json-output"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["name"] == "My Panel"
        assert "panel_id" in data

    def test_with_description(self, runner: CliRunner, tmp_path: Path):
        out = tmp_path / "p.json"
        result = runner.invoke(cli, ["init", "P", "--description", "desc", "--output", str(out)])
        assert result.exit_code == 0, result.output
        from synthetic_panel.storage import load_panel
        p = load_panel(out)
        assert p.description == "desc"


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------

class TestAddCommand:
    def test_adds_participant(self, runner: CliRunner, panel_file: Path):
        result = runner.invoke(cli, [
            "add", "--panel", str(panel_file),
            "--name", "Charlie",
            "--archetype", "Explorer",
            "--segment", "Early Adopter",
        ])
        assert result.exit_code == 0, result.output
        from synthetic_panel.storage import load_panel
        p = load_panel(panel_file)
        assert len(p.participants) == 1

    def test_json_output(self, runner: CliRunner, panel_file: Path):
        result = runner.invoke(cli, [
            "add", "--panel", str(panel_file),
            "--name", "Dana",
            "--archetype", "Doubter",
            "--segment", "Mid-market",
            "--json-output",
        ])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["name"] == "Dana"
        assert len(data["versions"]) == 1

    def test_with_attributes(self, runner: CliRunner, panel_file: Path):
        attrs = json.dumps({"comfort": "high", "device": "iOS"})
        result = runner.invoke(cli, [
            "add", "--panel", str(panel_file),
            "--name", "Eve",
            "--archetype", "Power User",
            "--segment", "YP",
            "--attributes", attrs,
        ])
        assert result.exit_code == 0, result.output
        from synthetic_panel.storage import load_panel
        p = load_panel(panel_file)
        pt = list(p.participants.values())[0]
        assert pt.attributes["device"] == "iOS"

    def test_with_tags(self, runner: CliRunner, panel_file: Path):
        result = runner.invoke(cli, [
            "add", "--panel", str(panel_file),
            "--name", "Frank",
            "--archetype", "A",
            "--segment", "S",
            "--tags", "t1,t2,t3",
        ])
        assert result.exit_code == 0, result.output
        from synthetic_panel.storage import load_panel
        p = load_panel(panel_file)
        pt = list(p.participants.values())[0]
        assert "t1" in pt.tags
        assert "t3" in pt.tags

    def test_invalid_json_attributes(self, runner: CliRunner, panel_file: Path):
        result = runner.invoke(cli, [
            "add", "--panel", str(panel_file),
            "--name", "G",
            "--archetype", "A",
            "--segment", "S",
            "--attributes", "not-json",
        ])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

class TestListCommand:
    def test_lists_participants(self, runner: CliRunner, populated_panel_file: Path):
        result = runner.invoke(cli, ["list", "--panel", str(populated_panel_file)])
        assert result.exit_code == 0, result.output
        assert "Alice" in result.output
        assert "Bob" in result.output

    def test_filter_by_archetype(self, runner: CliRunner, populated_panel_file: Path):
        result = runner.invoke(cli, [
            "list", "--panel", str(populated_panel_file),
            "--archetype", "Power User",
        ])
        assert result.exit_code == 0, result.output
        assert "Alice" in result.output
        assert "Bob" not in result.output

    def test_json_output(self, runner: CliRunner, populated_panel_file: Path):
        result = runner.invoke(cli, [
            "list", "--panel", str(populated_panel_file), "--json-output",
        ])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 2

    def test_empty_panel(self, runner: CliRunner, panel_file: Path):
        result = runner.invoke(cli, ["list", "--panel", str(panel_file)])
        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

class TestUpdateCommand:
    def test_updates_field(self, runner: CliRunner, populated_panel_file: Path):
        pid = _get_first_pid(populated_panel_file)
        result = runner.invoke(cli, [
            "update", "--panel", str(populated_panel_file),
            pid,
            "--updates", '{"archetype": "Super User"}',
        ])
        assert result.exit_code == 0, result.output
        from synthetic_panel.storage import load_panel
        p = load_panel(populated_panel_file)
        assert p.participants[pid].archetype == "Super User"

    def test_version_bumped(self, runner: CliRunner, populated_panel_file: Path):
        pid = _get_first_pid(populated_panel_file)
        runner.invoke(cli, [
            "update", "--panel", str(populated_panel_file),
            pid,
            "--updates", '{"segment": "Senior"}',
        ])
        from synthetic_panel.storage import load_panel
        p = load_panel(populated_panel_file)
        assert p.participants[pid].current_version == 2

    def test_prefix_resolution(self, runner: CliRunner, populated_panel_file: Path):
        pid = _get_first_pid(populated_panel_file)
        prefix = pid[:8]
        result = runner.invoke(cli, [
            "update", "--panel", str(populated_panel_file),
            prefix,
            "--updates", '{"archetype": "Changed"}',
        ])
        assert result.exit_code == 0, result.output

    def test_invalid_json(self, runner: CliRunner, populated_panel_file: Path):
        pid = _get_first_pid(populated_panel_file)
        result = runner.invoke(cli, [
            "update", "--panel", str(populated_panel_file),
            pid, "--updates", "bad-json",
        ])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# assign
# ---------------------------------------------------------------------------

class TestAssignCommand:
    def test_assigns_participants(self, runner: CliRunner, populated_panel_file: Path):
        pid = _get_first_pid(populated_panel_file)
        result = runner.invoke(cli, [
            "assign", "--panel", str(populated_panel_file),
            "--study-id", "study-01",
            "--study-name", "Wave 1",
            "--participants", pid,
        ])
        assert result.exit_code == 0, result.output
        from synthetic_panel.storage import load_panel
        p = load_panel(populated_panel_file)
        assert len(p.assignments) == 1

    def test_json_output(self, runner: CliRunner, populated_panel_file: Path):
        pid = _get_first_pid(populated_panel_file)
        result = runner.invoke(cli, [
            "assign", "--panel", str(populated_panel_file),
            "--study-id", "study-01",
            "--study-name", "Wave 1",
            "--participants", pid,
            "--json-output",
        ])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert data[0]["study_id"] == "study-01"


# ---------------------------------------------------------------------------
# log
# ---------------------------------------------------------------------------

class TestLogCommand:
    def test_logs_session(self, runner: CliRunner, populated_panel_file: Path):
        pid = _get_first_pid(populated_panel_file)
        result = runner.invoke(cli, [
            "log", "--panel", str(populated_panel_file),
            "--study-id", "study-01",
            "--participant-id", pid,
            "--responses", '{"sus": 75}',
        ])
        assert result.exit_code == 0, result.output
        from synthetic_panel.storage import load_panel
        p = load_panel(populated_panel_file)
        assert len(p.sessions) == 1

    def test_json_output(self, runner: CliRunner, populated_panel_file: Path):
        pid = _get_first_pid(populated_panel_file)
        result = runner.invoke(cli, [
            "log", "--panel", str(populated_panel_file),
            "--study-id", "study-01",
            "--participant-id", pid,
            "--responses", '{"score": 90}',
            "--json-output",
        ])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["responses"]["score"] == 90


# ---------------------------------------------------------------------------
# history
# ---------------------------------------------------------------------------

class TestHistoryCommand:
    def test_shows_history(self, runner: CliRunner, populated_panel_file: Path):
        pid = _get_first_pid(populated_panel_file)
        result = runner.invoke(cli, [
            "history", "--panel", str(populated_panel_file), pid,
        ])
        assert result.exit_code == 0, result.output

    def test_json_output(self, runner: CliRunner, populated_panel_file: Path):
        pid = _get_first_pid(populated_panel_file)
        result = runner.invoke(cli, [
            "history", "--panel", str(populated_panel_file), pid, "--json-output",
        ])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert "participant" in data
        assert "version_count" in data


# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------

class TestSummaryCommand:
    def test_shows_summary(self, runner: CliRunner, populated_panel_file: Path):
        result = runner.invoke(cli, ["summary", "--panel", str(populated_panel_file)])
        assert result.exit_code == 0, result.output

    def test_json_output(self, runner: CliRunner, populated_panel_file: Path):
        result = runner.invoke(cli, [
            "summary", "--panel", str(populated_panel_file), "--json-output",
        ])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["participant_count"] == 2
        assert "archetypes" in data
        assert "segments" in data


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

class TestExportCommand:
    def test_exports_all(self, runner: CliRunner, populated_panel_file: Path, tmp_path: Path):
        out_dir = tmp_path / "exports"
        result = runner.invoke(cli, [
            "export", "--panel", str(populated_panel_file),
            "--type", "all",
            "--output-dir", str(out_dir),
        ])
        assert result.exit_code == 0, result.output
        assert (out_dir / "participants.json").exists()
        assert (out_dir / "sessions.json").exists()
        assert (out_dir / "assignments.json").exists()

    def test_exports_participants_only(self, runner: CliRunner, populated_panel_file: Path, tmp_path: Path):
        out_dir = tmp_path / "out"
        result = runner.invoke(cli, [
            "export", "--panel", str(populated_panel_file),
            "--type", "participants",
            "--output-dir", str(out_dir),
        ])
        assert result.exit_code == 0, result.output
        assert (out_dir / "participants.json").exists()
        assert not (out_dir / "sessions.json").exists()


# ---------------------------------------------------------------------------
# diff
# ---------------------------------------------------------------------------

class TestDiffCommand:
    def test_diff_between_versions(self, runner: CliRunner, populated_panel_file: Path):
        pid = _get_first_pid(populated_panel_file)
        # Create v2
        runner.invoke(cli, [
            "update", "--panel", str(populated_panel_file),
            pid, "--updates", '{"archetype": "Super User"}',
        ])
        result = runner.invoke(cli, [
            "diff", "--panel", str(populated_panel_file),
            pid, "--version-a", "1", "--version-b", "2",
        ])
        assert result.exit_code == 0, result.output

    def test_diff_json_output(self, runner: CliRunner, populated_panel_file: Path):
        pid = _get_first_pid(populated_panel_file)
        runner.invoke(cli, [
            "update", "--panel", str(populated_panel_file),
            pid, "--updates", '{"segment": "Senior"}',
        ])
        result = runner.invoke(cli, [
            "diff", "--panel", str(populated_panel_file),
            pid, "--version-a", "1", "--version-b", "2", "--json-output",
        ])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert "changed_fields" in data


# ---------------------------------------------------------------------------
# study
# ---------------------------------------------------------------------------

class TestStudyCommand:
    def test_shows_study_assignments(self, runner: CliRunner, populated_panel_file: Path):
        pid = _get_first_pid(populated_panel_file)
        runner.invoke(cli, [
            "assign", "--panel", str(populated_panel_file),
            "--study-id", "study-01",
            "--study-name", "Wave 1",
            "--participants", pid,
        ])
        result = runner.invoke(cli, [
            "study", "--panel", str(populated_panel_file), "study-01",
        ])
        assert result.exit_code == 0, result.output

    def test_empty_study(self, runner: CliRunner, populated_panel_file: Path):
        result = runner.invoke(cli, [
            "study", "--panel", str(populated_panel_file), "nonexistent-study",
        ])
        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# remove
# ---------------------------------------------------------------------------

class TestRemoveCommand:
    def test_removes_participant(self, runner: CliRunner, populated_panel_file: Path):
        pid = _get_first_pid(populated_panel_file)
        result = runner.invoke(cli, [
            "remove", "--panel", str(populated_panel_file), pid,
        ])
        assert result.exit_code == 0, result.output
        from synthetic_panel.storage import load_panel
        p = load_panel(populated_panel_file)
        assert pid not in p.participants

    def test_json_output(self, runner: CliRunner, populated_panel_file: Path):
        pid = _get_first_pid(populated_panel_file)
        result = runner.invoke(cli, [
            "remove", "--panel", str(populated_panel_file), pid, "--json-output",
        ])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["removed"] == pid

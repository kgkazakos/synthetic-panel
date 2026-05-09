"""
basic_usage.py — synthetic-panel quickstart

Demonstrates creating a panel, adding versioned participants,
assigning them to studies, logging sessions, and exporting data.
"""

from synthetic_panel.panel import (
    add_participant,
    assign_to_study,
    compare_participant_versions,
    create_panel,
    get_participant_history,
    log_session,
    panel_summary,
    update_participant,
)
from synthetic_panel.storage import export_participants, export_sessions, save_panel

# ── 1. Create a panel ──────────────────────────────────────────────────────
panel = create_panel(
    "Mobile Banking UX Panel",
    "Longitudinal synthetic panel for mobile banking research",
)

# ── 2. Add participants ────────────────────────────────────────────────────
alex = add_participant(
    panel,
    name="Alex Chen",
    archetype="Power User",
    segment="Young Professional",
    attributes={
        "age_range": "25-34",
        "tech_comfort": "high",
        "primary_device": "iOS",
        "banking_frequency": "daily",
    },
    tags=["digital-native", "high-value"],
    note="Recruited for Wave 1",
)

maria = add_participant(
    panel,
    name="Maria Santos",
    archetype="Cautious Saver",
    segment="Mid-career",
    attributes={
        "age_range": "35-44",
        "tech_comfort": "medium",
        "primary_device": "Android",
        "banking_frequency": "weekly",
    },
    tags=["savings-focused", "privacy-aware"],
    note="Recruited for Wave 1",
)

print(f"Panel has {len(panel.participants)} participants")

# ── 3. Assign to Wave 1 study ──────────────────────────────────────────────
assign_to_study(
    panel,
    study_id="wave-1",
    study_name="Wave 1 — Onboarding Usability",
    participant_ids=[alex.id, maria.id],
)

# ── 4. Log Wave 1 sessions ─────────────────────────────────────────────────
log_session(
    panel,
    study_id="wave-1",
    participant_id=alex.id,
    responses={
        "task_completion_rate": 0.85,
        "sus_score": 72,
        "top_pain_point": "Transfer limit too low",
        "would_recommend": True,
    },
    notes="Smooth session; flagged transfer cap unprompted",
)

log_session(
    panel,
    study_id="wave-1",
    participant_id=maria.id,
    responses={
        "task_completion_rate": 0.60,
        "sus_score": 55,
        "top_pain_point": "Bill pay buried in menus",
        "would_recommend": False,
    },
    notes="Struggled with navigation; completed savings goal easily",
)

# ── 5. Update Alex after Wave 1 (new version created) ─────────────────────
update_participant(
    panel,
    participant_id=alex.id,
    updates={
        "tags": ["digital-native", "high-value", "crypto-curious"],
        "attributes": {
            "age_range": "25-34",
            "tech_comfort": "high",
            "primary_device": "iOS",
            "banking_frequency": "daily",
            "crypto_interest": True,           # <-- emerged post Wave 1
        },
    },
    note="Post-Wave-1 update — crypto interest surfaced",
)

print(f"Alex is now at version {alex.current_version}")

# ── 6. Assign Alex to Wave 2 at new version ───────────────────────────────
assign_to_study(
    panel,
    study_id="wave-2",
    study_name="Wave 2 — Post-redesign Follow-up",
    participant_ids=[alex.id],
    notes="Alex re-engaged after crypto feature shipped",
)

log_session(
    panel,
    study_id="wave-2",
    participant_id=alex.id,
    responses={
        "task_completion_rate": 0.95,
        "sus_score": 82,
        "top_pain_point": "None major",
        "would_recommend": True,
    },
    notes="Clear improvement vs Wave 1 baseline",
)

# ── 7. Compare Alex v1 vs v2 ──────────────────────────────────────────────
diff = compare_participant_versions(panel, alex.id, 1, 2)
print(f"Changed fields between v1 and v2: {diff['changed_fields']}")

# ── 8. Participant history ─────────────────────────────────────────────────
history = get_participant_history(panel, alex.id)
print(
    f"Alex: {history['version_count']} versions, "
    f"{history['study_count']} studies, "
    f"{history['session_count']} sessions"
)

# ── 9. Panel summary ──────────────────────────────────────────────────────
summary = panel_summary(panel)
print(f"Panel summary: {summary['participant_count']} participants, {summary['study_count']} studies")

# ── 10. Save and export ───────────────────────────────────────────────────
save_panel(panel, "panel.json")
export_participants(panel, "participants.json")
export_sessions(panel, "sessions.json")
print("Saved panel.json, participants.json, sessions.json")

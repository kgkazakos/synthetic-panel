"""Streamlit UI for synthetic-panel."""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from synthetic_panel.models import Panel
from synthetic_panel.panel import (
    add_participant,
    assign_to_study,
    compare_participant_versions,
    create_panel,
    filter_participants,
    get_participant_history,
    log_session,
    panel_summary,
    update_participant,
)
from synthetic_panel.storage import (
    load_panel,
    save_panel,
)

st.set_page_config(
    page_title="synthetic-panel",
    page_icon="👥",
    layout="wide",
)

PANEL_PATH = Path("panel.json")

# ---------------------------------------------------------------------------
# Session state bootstrap
# ---------------------------------------------------------------------------

if "panel" not in st.session_state:
    if PANEL_PATH.exists():
        st.session_state.panel = load_panel(PANEL_PATH)
    else:
        st.session_state.panel = create_panel("My Research Panel")
        save_panel(st.session_state.panel, PANEL_PATH)


def _save() -> None:
    save_panel(st.session_state.panel, PANEL_PATH)


panel: Panel = st.session_state.panel

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("👥 synthetic-panel")
st.caption("Persistent, versioned synthetic research participant management — CPR Orbital Tool 20")

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tabs = st.tabs(["📊 Overview", "👤 Participants", "🗂 Studies", "📝 Sessions", "🔄 History", "📤 Export"])

# ─── Overview ───────────────────────────────────────────────────────────────

with tabs[0]:
    summary = panel_summary(panel)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Participants", summary["participant_count"])
    col2.metric("Studies", summary["study_count"])
    col3.metric("Sessions", summary["session_count"])
    col4.metric("Assignments", summary["assignment_count"])

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("By Archetype")
        if summary["archetypes"]:
            for arch, count in sorted(summary["archetypes"].items(), key=lambda x: -x[1]):
                st.progress(count / summary["participant_count"], text=f"{arch} ({count})")
        else:
            st.caption("No participants yet.")

    with c2:
        st.subheader("By Segment")
        if summary["segments"]:
            for seg, count in sorted(summary["segments"].items(), key=lambda x: -x[1]):
                st.progress(count / summary["participant_count"], text=f"{seg} ({count})")
        else:
            st.caption("No participants yet.")

    st.divider()
    with st.expander("Panel settings"):
        new_name = st.text_input("Panel name", value=panel.name)
        new_desc = st.text_area("Description", value=panel.description, height=80)
        if st.button("Save settings"):
            panel.name = new_name
            panel.description = new_desc
            _save()
            st.success("Settings saved.")
            st.rerun()

# ─── Participants ────────────────────────────────────────────────────────────

with tabs[1]:
    st.subheader("Add participant")
    with st.form("add_form"):
        fc1, fc2 = st.columns(2)
        p_name = fc1.text_input("Name *")
        p_archetype = fc2.text_input("Archetype *")
        fc3, fc4 = st.columns(2)
        p_segment = fc3.text_input("Segment *")
        p_tags = fc4.text_input("Tags (comma-separated)")
        p_attrs = st.text_area("Attributes (JSON)", value="{}", height=80)
        p_note = st.text_input("Version note", value="Initial version")
        submitted = st.form_submit_button("Add participant")
        if submitted:
            if not p_name or not p_archetype or not p_segment:
                st.error("Name, archetype, and segment are required.")
            else:
                try:
                    attrs = json.loads(p_attrs)
                except json.JSONDecodeError:
                    st.error("Attributes must be valid JSON.")
                else:
                    tag_list = [t.strip() for t in p_tags.split(",") if t.strip()]
                    add_participant(panel, p_name, p_archetype, p_segment, attrs, tag_list, p_note)
                    _save()
                    st.success(f"Added '{p_name}'")
                    st.rerun()

    st.divider()
    st.subheader("Participant roster")

    fc1, fc2, fc3 = st.columns(3)
    f_arch = fc1.text_input("Filter archetype")
    f_seg = fc2.text_input("Filter segment")
    f_tag = fc3.text_input("Filter tag")

    filtered = filter_participants(
        panel,
        archetype=f_arch or None,
        segment=f_seg or None,
        tags=[f_tag] if f_tag else None,
    )

    if not filtered:
        st.caption("No participants match.")
    else:
        for pt in filtered:
            with st.expander(f"**{pt.name}** — {pt.archetype} / {pt.segment}  (v{pt.current_version})"):
                sc1, sc2 = st.columns(2)
                sc1.markdown(f"**ID:** `{pt.id[:12]}…`")
                sc2.markdown(f"**Tags:** {', '.join(pt.tags) or '—'}")
                st.json(pt.attributes)

                with st.form(f"update_{pt.id}"):
                    upd_json = st.text_area("Updates (JSON)", value="{}", height=70, key=f"upd_{pt.id}")
                    upd_note = st.text_input("Note", key=f"note_{pt.id}")
                    if st.form_submit_button("Update → new version"):
                        try:
                            upd = json.loads(upd_json)
                        except json.JSONDecodeError:
                            st.error("Updates must be valid JSON.")
                        else:
                            update_participant(panel, pt.id, upd, upd_note)
                            _save()
                            st.success(f"Updated → v{pt.current_version}")
                            st.rerun()

# ─── Studies ─────────────────────────────────────────────────────────────────

with tabs[2]:
    st.subheader("Assign participants to a study")
    if not panel.participants:
        st.caption("Add participants first.")
    else:
        participant_options = {
            f"{pt.name} ({pt.archetype})": pid
            for pid, pt in panel.participants.items()
        }
        with st.form("assign_form"):
            s_id = st.text_input("Study ID *")
            s_name = st.text_input("Study name *")
            s_parts = st.multiselect("Participants *", options=list(participant_options.keys()))
            s_notes = st.text_input("Notes")
            if st.form_submit_button("Assign"):
                if not s_id or not s_name or not s_parts:
                    st.error("Study ID, name, and at least one participant are required.")
                else:
                    pids = [participant_options[name] for name in s_parts]
                    assign_to_study(panel, s_id, s_name, pids, s_notes)
                    _save()
                    st.success(f"Assigned {len(pids)} participant(s) to '{s_name}'")
                    st.rerun()

    st.divider()
    st.subheader("Study roster")
    studies: dict[str, str] = {a.study_id: a.study_name for a in panel.assignments}
    if not studies:
        st.caption("No studies yet.")
    else:
        for sid, sname in studies.items():
            study_assignments = [a for a in panel.assignments if a.study_id == sid]
            with st.expander(f"**{sname}** ({sid}) — {len(study_assignments)} participant(s)"):
                for a in study_assignments:
                    pt = panel.participants.get(a.participant_id)
                    st.markdown(
                        f"- **{pt.name if pt else '—'}** "
                        f"(v{a.participant_version}) assigned {a.assigned_at[:10]}"
                    )

# ─── Sessions ────────────────────────────────────────────────────────────────

with tabs[3]:
    st.subheader("Log a session")
    if not panel.participants:
        st.caption("Add participants first.")
    else:
        participant_options = {
            f"{pt.name} ({pt.archetype})": pid
            for pid, pt in panel.participants.items()
        }
        with st.form("log_form"):
            ls_study = st.text_input("Study ID *")
            ls_part = st.selectbox("Participant *", options=list(participant_options.keys()))
            ls_resp = st.text_area("Responses (JSON)", value="{}", height=100)
            ls_notes = st.text_input("Notes")
            if st.form_submit_button("Log session"):
                if not ls_study:
                    st.error("Study ID is required.")
                else:
                    try:
                        resp = json.loads(ls_resp)
                    except json.JSONDecodeError:
                        st.error("Responses must be valid JSON.")
                    else:
                        pid = participant_options[ls_part]
                        log_session(panel, ls_study, pid, resp, ls_notes)
                        _save()
                        st.success("Session logged.")
                        st.rerun()

    st.divider()
    st.subheader("Session log")
    if not panel.sessions:
        st.caption("No sessions logged yet.")
    else:
        for s in reversed(panel.sessions):
            pt = panel.participants.get(s.participant_id)
            with st.expander(
                f"{s.session_date[:10]} — **{pt.name if pt else '—'}** in study `{s.study_id}` (v{s.participant_version})"
            ):
                st.json(s.responses)
                if s.notes:
                    st.caption(s.notes)

# ─── History ─────────────────────────────────────────────────────────────────

with tabs[4]:
    st.subheader("Participant history")
    if not panel.participants:
        st.caption("No participants yet.")
    else:
        participant_options = {
            f"{pt.name} ({pt.archetype})": pid
            for pid, pt in panel.participants.items()
        }
        selected = st.selectbox("Select participant", options=list(participant_options.keys()))
        if selected:
            pid = participant_options[selected]
            history = get_participant_history(panel, pid)
            pt = panel.participants[pid]

            hc1, hc2, hc3 = st.columns(3)
            hc1.metric("Versions", history["version_count"])
            hc2.metric("Studies", history["study_count"])
            hc3.metric("Sessions", history["session_count"])

            st.divider()
            st.subheader("Version timeline")
            for v in pt.versions:
                with st.expander(f"v{v.version} — {v.created_at[:10]}  {v.note or ''}"):
                    st.json(v.snapshot)

            if pt.current_version >= 2:
                st.divider()
                st.subheader("Version diff")
                dc1, dc2 = st.columns(2)
                va = dc1.number_input("Version A", min_value=1, max_value=pt.current_version, value=1)
                vb = dc2.number_input("Version B", min_value=1, max_value=pt.current_version, value=pt.current_version)
                if st.button("Compare"):
                    diff = compare_participant_versions(panel, pid, int(va), int(vb))
                    if "error" in diff:
                        st.error(diff["error"])
                    elif not diff["changed_fields"]:
                        st.info("No differences between these versions.")
                    else:
                        st.markdown(f"**Changed fields:** {', '.join(diff['changed_fields'])}")
                        st.json(diff["diffs"])

# ─── Export ──────────────────────────────────────────────────────────────────

with tabs[5]:
    st.subheader("Export panel data")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Participants JSON**")
        parts_data = json.dumps([p.to_dict() for p in panel.participants.values()], indent=2)
        st.download_button(
            "⬇ Download participants.json",
            data=parts_data,
            file_name="participants.json",
            mime="application/json",
        )

    with col2:
        st.markdown("**Sessions JSON**")
        sess_data = json.dumps([s.to_dict() for s in panel.sessions], indent=2)
        st.download_button(
            "⬇ Download sessions.json",
            data=sess_data,
            file_name="sessions.json",
            mime="application/json",
        )

    st.divider()
    st.markdown("**Full panel JSON**")
    full_data = json.dumps(panel.to_dict(), indent=2)
    st.download_button(
        "⬇ Download panel.json",
        data=full_data,
        file_name="panel.json",
        mime="application/json",
    )

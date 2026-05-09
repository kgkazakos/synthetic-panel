# synthetic-panel

**Persistent, versioned synthetic research participant management.**

`synthetic-panel` solves a quiet problem in longitudinal synthetic research: participants generated fresh for every study carry no memory, no history, and no continuity. This tool maintains a structured panel — a persistent roster of synthetic participants whose profiles evolve across study waves, with every version snapshotted and every session logged.

Part of the [CPR Orbital series](https://github.com/kgkazakos) — Tool 20 of 40.

---

## The problem

Running longitudinal studies with synthetic participants usually means:

- Generating a new participant from scratch each time
- Losing the thread of how an archetype's attitudes evolved
- No way to compare how a participant responded to v1 vs v2 of a feature
- No institutional memory across your synthetic research corpus

`synthetic-panel` gives your synthetic participants a persistent identity.

---

## Features

- **Panel registry** — create and manage a named roster of synthetic participants with rich attribute profiles
- **Version control** — every update snapshots a new version; full timeline preserved
- **Study assignment** — assign panel subsets to studies at their current version; participants are stamped at point of assignment
- **Session logging** — record responses per participant per study wave with version tracking
- **Version diff** — compare any two snapshots of a participant to surface what changed
- **Cross-study history** — see every study, assignment, and session for any participant
- **JSON export** — outputs participants, sessions, and assignments for downstream tools
- **Streamlit UI** — visual panel management with download support
- **CLI** — full command set for scripting and CI integration

---

## Installation

```bash
pip install synthetic-panel
```

With Streamlit UI:

```bash
pip install "synthetic-panel[ui]"
```

---

## CLI quickstart

```bash
# Create a panel
synthetic-panel init "Mobile Banking Panel" --output panel.json

# Add participants
synthetic-panel add --name "Alex Chen" --archetype "Power User" \
  --segment "Young Professional" \
  --attributes '{"tech_comfort": "high", "device": "iOS"}' \
  --tags "digital-native,high-value"

# List participants
synthetic-panel list

# Assign to a study (version snapshotted at assignment)
synthetic-panel assign --study-id "wave-1" --study-name "Wave 1 Usability" \
  --participants <participant-id>

# Log a session
synthetic-panel log --study-id "wave-1" --participant-id <id> \
  --responses '{"sus_score": 72, "completed": true}'

# Update a participant → new version created
synthetic-panel update <participant-id> \
  --updates '{"tags": ["digital-native", "crypto-curious"]}' \
  --note "Post-Wave-1 update"

# Compare versions
synthetic-panel diff <participant-id> --version-a 1 --version-b 2

# Participant cross-study history
synthetic-panel history <participant-id>

# Panel summary
synthetic-panel summary

# Export all data
synthetic-panel export --type all --output-dir ./exports
```

All commands support `--json-output` for CI integration.

---

## Streamlit UI

```bash
streamlit run synthetic_panel/app.py
```

The app provides tabs for panel overview, participant management, study assignment, session logging, history tracking, and export.

---

## Python API

```python
from synthetic_panel.panel import (
    create_panel, add_participant, update_participant,
    assign_to_study, log_session, get_participant_history,
    compare_participant_versions, panel_summary,
)
from synthetic_panel.storage import save_panel, load_panel

# Create and populate
panel = create_panel("My Panel")
alex = add_participant(panel, "Alex", "Power User", "YP", {"device": "iOS"})

# Study wave 1
assign_to_study(panel, "wave-1", "Wave 1", [alex.id])
log_session(panel, "wave-1", alex.id, {"sus_score": 72})

# Evolve the participant
update_participant(panel, alex.id, {"tags": ["crypto-curious"]}, note="Post-Wave-1")

# Study wave 2 — Alex assigned at v2
assign_to_study(panel, "wave-2", "Wave 2", [alex.id])
log_session(panel, "wave-2", alex.id, {"sus_score": 82})

# Diff v1 vs v2
diff = compare_participant_versions(panel, alex.id, 1, 2)

# Persist
save_panel(panel, "panel.json")
```

---

## Design principles

**Version continuity over fresh generation.** When a participant evolves, the original snapshot is preserved. You can always reconstruct who they were at any study wave.

**Version stamped at assignment.** When you assign a participant to a study, their current version is recorded on the assignment. This means you know exactly which profile was active when the study ran — even if the participant is updated later.

**No LLM required.** The core panel is fully rule-based. Participants are data structures. All operations run offline without API calls. LLM-generated participant profiles can be added via the attributes field — `synthetic-panel` stores and versions whatever you put there.

---

## Part of the CPR Ecosystem

`synthetic-panel` connects with:

- [`synthetic-participants`](https://github.com/kgkazakos/synthetic-participants) — generate richly profiled participants to populate your panel
- [`persona-forge`](https://github.com/kgkazakos/persona-forge) — controlled persona generation with behavioural consistency validation
- [`interview-sim`](https://github.com/kgkazakos/interview-sim) — simulate full interview sessions for panelled participants
- [`guide-scorer`](https://github.com/kgkazakos/guide-scorer) — score discussion guides before running panel sessions
- [`insight-differ`](https://github.com/kgkazakos/insight-differ) — compare research reports across panel waves

Part of the **CPR Orbital** series — 40 open-source tools for AI-native product research, shipping almost daily.

---

## License

MIT © Kostas Kazakos

---

## LLM enrichment (optional)

`synthetic-panel` runs fully rule-based with zero API calls. When you want to go further, the optional LLM layer adds two capabilities powered by DSPy ChainOfThought:

**1. Drift suggestion (`evolve`)** — given a participant's current profile and their session history across study waves, an LLM suggests how their attributes, attitudes, and behaviours might plausibly evolve for the next wave. You can inspect the suggestion or apply it directly as a new version.

**2. Profile generation (`generate`)** — given an archetype and segment brief, an LLM generates a richly profiled participant with realistic attributes and tags, ready to add to the panel.

### Install

```bash
pip install "synthetic-panel[llm]"
```

Supported backends: OpenAI, Anthropic, Gemini. Set the relevant API key as an environment variable (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`).

### Drift suggestion

```bash
# Suggest how Alex might evolve after a redesign — inspect only
synthetic-panel evolve <participant-id> \
  --study-context "Redesigned nav, raised transfer limits, added crypto feature" \
  --llm-backend anthropic

# Suggest and apply as a new version
synthetic-panel evolve <participant-id> \
  --study-context "Redesigned nav, raised transfer limits, added crypto feature" \
  --llm-backend anthropic \
  --apply
```

The `--apply` flag writes the suggested updates as a new version snapshot, with the LLM's `version_note` recorded in the version timeline.

### Profile generation

```bash
# Generate a participant and add directly to the panel
synthetic-panel generate \
  --archetype "Cautious Saver" \
  --segment "Near Retirement" \
  --study-context "Mobile banking app with budgeting and investment features" \
  --llm-backend openai \
  --add-to-panel
```

### Python API

```python
from synthetic_panel.llm import configure_backend, suggest_drift, generate_profile

configure_backend("anthropic")  # or "openai" / "gemini"

# Suggest drift
suggestion = suggest_drift(
    participant_profile=participant.to_dict(),
    session_history=[s.to_dict() for s in sessions],
    study_context="Raised transfer limits, added crypto onboarding",
)
print(suggestion["drift_rationale"])
print(suggestion["suggested_updates"])

# Generate a new participant profile
profile = generate_profile(
    archetype="Power User",
    segment="Young Professional",
    study_context="Mobile banking app",
)
```

> **Note:** LLM scaffolding is reference-only and not executed in CI. The rule-based core is fully tested independently of any API calls.

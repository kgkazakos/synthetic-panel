"""LLM enrichment layer for synthetic-panel.

Uses DSPy ChainOfThought to suggest attribute drift for a participant
based on their session history across study waves.

This module is reference scaffolding — not executed in CI.
Requires: pip install "synthetic-panel[llm]"
"""
from __future__ import annotations

import json
from typing import Any

try:
    import dspy
    DSPY_AVAILABLE = True
except ImportError:
    DSPY_AVAILABLE = False


# ---------------------------------------------------------------------------
# LLM backend configuration
# ---------------------------------------------------------------------------

SUPPORTED_BACKENDS = {
    "openai": "openai/gpt-4o-mini",
    "anthropic": "anthropic/claude-haiku-4-5-20251001",
    "gemini": "gemini/gemini-3.6-flash",
}


def configure_backend(backend: str) -> None:
    """Configure DSPy LM for the specified backend."""
    if not DSPY_AVAILABLE:
        raise ImportError(
            "DSPy is required for LLM enrichment. "
            "Install with: pip install 'synthetic-panel[llm]'"
        )
    model_string = SUPPORTED_BACKENDS.get(backend)
    if model_string is None:
        raise ValueError(
            f"Unsupported backend '{backend}'. "
            f"Choose from: {', '.join(SUPPORTED_BACKENDS)}"
        )
    lm = dspy.LM(model_string)
    dspy.configure(lm=lm)


# ---------------------------------------------------------------------------
# DSPy signatures
# ---------------------------------------------------------------------------

if DSPY_AVAILABLE:
    class ParticipantDriftSignature(dspy.Signature):
        """Suggest realistic attribute drift for a synthetic research participant.

        Given a participant's current profile and their session history across
        study waves, suggest how their attributes, attitudes, and behaviours
        might plausibly evolve for the next study wave.

        Return a JSON object with:
        - suggested_updates: dict of field -> new value for attributes that should change
        - drift_rationale: short plain-language explanation of why these changes are plausible
        - stability_notes: attributes that should remain stable and why
        - version_note: a one-line note suitable for the version snapshot
        """
        participant_profile: str = dspy.InputField(
            desc="Current participant profile as JSON string"
        )
        session_history: str = dspy.InputField(
            desc="Chronological session history as JSON string — responses, pain points, scores"
        )
        study_context: str = dspy.InputField(
            desc="Brief description of what changed between waves (e.g. redesigned nav, new feature)"
        )
        drift_suggestion: str = dspy.OutputField(
            desc="JSON object with suggested_updates, drift_rationale, stability_notes, version_note"
        )

    class ParticipantProfileSignature(dspy.Signature):
        """Generate a richly profiled synthetic research participant.

        Given a brief description of an archetype, segment, and study context,
        generate a detailed participant profile with realistic attributes,
        behavioural tendencies, and research-relevant characteristics.

        Return a JSON object with:
        - name: plausible full name
        - attributes: dict of relevant behavioural and demographic attributes
        - tags: list of 2-4 descriptive tags
        - generation_rationale: one sentence explaining the profile choices
        """
        archetype: str = dspy.InputField(desc="Participant archetype label")
        segment: str = dspy.InputField(desc="Market or demographic segment")
        study_context: str = dspy.InputField(
            desc="Brief description of the product or research area"
        )
        participant_profile: str = dspy.OutputField(
            desc="JSON object with name, attributes, tags, generation_rationale"
        )


# ---------------------------------------------------------------------------
# DSPy modules
# ---------------------------------------------------------------------------

if DSPY_AVAILABLE:
    class DriftSuggester(dspy.Module):
        """Suggests plausible attribute drift for a participant between study waves."""

        def __init__(self) -> None:
            super().__init__()
            self.suggest = dspy.ChainOfThought(ParticipantDriftSignature)

        def forward(
            self,
            participant_profile: str,
            session_history: str,
            study_context: str,
        ) -> dspy.Prediction:
            return self.suggest(
                participant_profile=participant_profile,
                session_history=session_history,
                study_context=study_context,
            )

    class ProfileGenerator(dspy.Module):
        """Generates a richly profiled synthetic participant from an archetype brief."""

        def __init__(self) -> None:
            super().__init__()
            self.generate = dspy.ChainOfThought(ParticipantProfileSignature)

        def forward(
            self,
            archetype: str,
            segment: str,
            study_context: str,
        ) -> dspy.Prediction:
            return self.generate(
                archetype=archetype,
                segment=segment,
                study_context=study_context,
            )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def suggest_drift(
    participant_profile: dict[str, Any],
    session_history: list[dict[str, Any]],
    study_context: str,
) -> dict[str, Any]:
    """Suggest attribute drift for a participant based on their session history.

    Args:
        participant_profile: Current participant dict (from Participant.to_dict())
        session_history: List of session log dicts for this participant
        study_context: Description of what changed between study waves

    Returns:
        Dict with suggested_updates, drift_rationale, stability_notes, version_note.
        Falls back to a structured null response if parsing fails.
    """
    if not DSPY_AVAILABLE:
        raise ImportError(
            "DSPy is required for LLM enrichment. "
            "Install with: pip install 'synthetic-panel[llm]'"
        )

    suggester = DriftSuggester()
    result = suggester(
        participant_profile=json.dumps(participant_profile, indent=2),
        session_history=json.dumps(session_history, indent=2),
        study_context=study_context,
    )

    raw = result.drift_suggestion
    # Strip markdown fences if present
    clean = raw.strip()
    if clean.startswith("```"):
        lines = clean.split("\n")
        clean = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    try:
        parsed = json.loads(clean)
    except json.JSONDecodeError:
        parsed = {
            "suggested_updates": {},
            "drift_rationale": raw,
            "stability_notes": "Could not parse structured output.",
            "version_note": "LLM drift suggestion (unstructured)",
        }

    return parsed


def generate_profile(
    archetype: str,
    segment: str,
    study_context: str,
) -> dict[str, Any]:
    """Generate a richly profiled synthetic participant from an archetype brief.

    Args:
        archetype: Participant archetype label (e.g. "Power User")
        segment: Market or demographic segment (e.g. "Young Professional")
        study_context: Brief description of the product or research area

    Returns:
        Dict with name, attributes, tags, generation_rationale.
    """
    if not DSPY_AVAILABLE:
        raise ImportError(
            "DSPy is required for LLM enrichment. "
            "Install with: pip install 'synthetic-panel[llm]'"
        )

    generator = ProfileGenerator()
    result = generator(
        archetype=archetype,
        segment=segment,
        study_context=study_context,
    )

    raw = result.participant_profile
    clean = raw.strip()
    if clean.startswith("```"):
        lines = clean.split("\n")
        clean = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    try:
        parsed = json.loads(clean)
    except json.JSONDecodeError:
        parsed = {
            "name": f"Synthetic {archetype}",
            "attributes": {},
            "tags": [],
            "generation_rationale": raw,
        }

    return parsed

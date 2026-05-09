"""Click CLI for synthetic-panel."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel as RichPanel
from rich.table import Table

from .models import Panel
from .panel import (
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
from .storage import (
    export_assignments,
    export_participants,
    export_sessions,
    load_panel,
    save_panel,
)

console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_or_exit(panel_path: str) -> Panel:
    path = Path(panel_path)
    if not path.exists():
        console.print(f"[red]Panel file not found: {panel_path}[/red]")
        sys.exit(1)
    return load_panel(path)


def _resolve_or_exit(panel: Panel, id_or_prefix: str) -> str:
    resolved = resolve_participant_id(panel, id_or_prefix)
    if resolved is None:
        console.print(f"[red]Participant not found or ambiguous: {id_or_prefix}[/red]")
        sys.exit(1)
    return resolved


# ---------------------------------------------------------------------------
# CLI root
# ---------------------------------------------------------------------------

@click.group()
def cli() -> None:
    """synthetic-panel — persistent, versioned synthetic research participant management."""


# ---------------------------------------------------------------------------
# Panel lifecycle
# ---------------------------------------------------------------------------

@cli.command("init")
@click.argument("name")
@click.option("--description", "-d", default="", help="Panel description")
@click.option("--output", "-o", default="panel.json", help="Output file path")
@click.option("--json-output", is_flag=True, help="JSON output")
def init_cmd(name: str, description: str, output: str, json_output: bool) -> None:
    """Create a new empty panel."""
    panel = create_panel(name, description)
    save_panel(panel, output)
    if json_output:
        click.echo(json.dumps({"panel_id": panel.id, "name": name, "path": output}))
    else:
        console.print(f"[green]✓[/green] Panel '[bold]{name}[/bold]' created → {output}")


# ---------------------------------------------------------------------------
# Participant commands
# ---------------------------------------------------------------------------

@cli.command("add")
@click.option("--panel", "-p", default="panel.json", help="Panel file")
@click.option("--name", "-n", required=True, help="Participant name")
@click.option("--archetype", "-a", required=True, help="Archetype label")
@click.option("--segment", "-s", required=True, help="Segment label")
@click.option("--attributes", default="{}", help="JSON dict of attributes")
@click.option("--tags", default="", help="Comma-separated tags")
@click.option("--note", default="Initial version", help="Version note")
@click.option("--json-output", is_flag=True)
def add_cmd(
    panel: str,
    name: str,
    archetype: str,
    segment: str,
    attributes: str,
    tags: str,
    note: str,
    json_output: bool,
) -> None:
    """Add a participant to the panel."""
    p = _load_or_exit(panel)
    try:
        attrs = json.loads(attributes)
    except json.JSONDecodeError:
        console.print("[red]--attributes must be valid JSON[/red]")
        sys.exit(1)
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    participant = add_participant(p, name, archetype, segment, attrs, tag_list, note)
    save_panel(p, panel)
    if json_output:
        click.echo(json.dumps(participant.to_dict()))
    else:
        console.print(
            f"[green]✓[/green] Added '[bold]{name}[/bold]' "
            f"(ID: {participant.id[:8]}…) — v1"
        )


@cli.command("list")
@click.option("--panel", "-p", default="panel.json")
@click.option("--archetype", default=None, help="Filter by archetype")
@click.option("--segment", default=None, help="Filter by segment")
@click.option("--tags", default=None, help="Filter by tags (comma-separated)")
@click.option("--json-output", is_flag=True)
def list_cmd(
    panel: str,
    archetype: str | None,
    segment: str | None,
    tags: str | None,
    json_output: bool,
) -> None:
    """List participants, with optional filters."""
    p = _load_or_exit(panel)
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    participants = filter_participants(p, archetype, segment, tag_list)
    if json_output:
        click.echo(json.dumps([pt.to_dict() for pt in participants]))
        return
    if not participants:
        console.print("[yellow]No participants match the filter.[/yellow]")
        return
    table = Table(title=f"Panel: {p.name}", show_lines=False)
    table.add_column("ID", style="dim", width=10)
    table.add_column("Name", style="bold")
    table.add_column("Archetype")
    table.add_column("Segment")
    table.add_column("Ver", justify="right", width=4)
    table.add_column("Tags")
    for pt in participants:
        table.add_row(
            pt.id[:8] + "…",
            pt.name,
            pt.archetype,
            pt.segment,
            str(pt.current_version),
            ", ".join(pt.tags),
        )
    console.print(table)


@cli.command("update")
@click.option("--panel", "-p", default="panel.json")
@click.argument("participant_id")
@click.option("--updates", "-u", required=True, help="JSON dict of fields to update")
@click.option("--note", default="", help="Version note")
@click.option("--json-output", is_flag=True)
def update_cmd(
    panel: str,
    participant_id: str,
    updates: str,
    note: str,
    json_output: bool,
) -> None:
    """Update a participant and snapshot a new version."""
    p = _load_or_exit(panel)
    pid = _resolve_or_exit(p, participant_id)
    try:
        upd = json.loads(updates)
    except json.JSONDecodeError:
        console.print("[red]--updates must be valid JSON[/red]")
        sys.exit(1)
    participant = update_participant(p, pid, upd, note)
    save_panel(p, panel)
    if json_output:
        click.echo(json.dumps(participant.to_dict()))
    else:
        console.print(
            f"[green]✓[/green] Updated '[bold]{participant.name}[/bold]' → v{participant.current_version}"
        )


@cli.command("remove")
@click.option("--panel", "-p", default="panel.json")
@click.argument("participant_id")
@click.option("--json-output", is_flag=True)
def remove_cmd(panel: str, participant_id: str, json_output: bool) -> None:
    """Remove a participant from the panel."""
    p = _load_or_exit(panel)
    pid = _resolve_or_exit(p, participant_id)
    name = p.participants[pid].name
    remove_participant(p, pid)
    save_panel(p, panel)
    if json_output:
        click.echo(json.dumps({"removed": pid, "name": name}))
    else:
        console.print(f"[green]✓[/green] Removed '{name}'")


# ---------------------------------------------------------------------------
# Study assignment
# ---------------------------------------------------------------------------

@cli.command("assign")
@click.option("--panel", "-p", default="panel.json")
@click.option("--study-id", required=True, help="Study identifier")
@click.option("--study-name", required=True, help="Study name")
@click.option("--participants", required=True, help="Comma-separated participant IDs or prefixes")
@click.option("--notes", default="", help="Assignment notes")
@click.option("--json-output", is_flag=True)
def assign_cmd(
    panel: str,
    study_id: str,
    study_name: str,
    participants: str,
    notes: str,
    json_output: bool,
) -> None:
    """Assign participants to a study at their current version."""
    p = _load_or_exit(panel)
    raw_ids = [i.strip() for i in participants.split(",") if i.strip()]
    resolved = [_resolve_or_exit(p, raw) for raw in raw_ids]
    assignments = assign_to_study(p, study_id, study_name, resolved, notes)
    save_panel(p, panel)
    if json_output:
        click.echo(json.dumps([a.to_dict() for a in assignments]))
    else:
        console.print(
            f"[green]✓[/green] Assigned {len(assignments)} participant(s) to '[bold]{study_name}[/bold]'"
        )


@cli.command("study")
@click.option("--panel", "-p", default="panel.json")
@click.argument("study_id")
@click.option("--json-output", is_flag=True)
def study_cmd(panel: str, study_id: str, json_output: bool) -> None:
    """Show all assignments for a study."""
    p = _load_or_exit(panel)
    assignments = get_study_assignments(p, study_id)
    if json_output:
        click.echo(json.dumps([a.to_dict() for a in assignments]))
        return
    if not assignments:
        console.print(f"[yellow]No assignments found for study: {study_id}[/yellow]")
        return
    table = Table(title=f"Study: {study_id}", show_lines=False)
    table.add_column("Participant", style="bold")
    table.add_column("Archetype")
    table.add_column("Ver", justify="right", width=4)
    table.add_column("Assigned At")
    for a in assignments:
        pt = p.participants.get(a.participant_id)
        table.add_row(
            pt.name if pt else a.participant_id[:8],
            pt.archetype if pt else "—",
            str(a.participant_version),
            a.assigned_at[:10],
        )
    console.print(table)


# ---------------------------------------------------------------------------
# Session logging
# ---------------------------------------------------------------------------

@cli.command("log")
@click.option("--panel", "-p", default="panel.json")
@click.option("--study-id", required=True, help="Study identifier")
@click.option("--participant-id", required=True, help="Participant ID or prefix")
@click.option("--responses", default="{}", help="JSON dict of responses")
@click.option("--notes", default="", help="Session notes")
@click.option("--json-output", is_flag=True)
def log_cmd(
    panel: str,
    study_id: str,
    participant_id: str,
    responses: str,
    notes: str,
    json_output: bool,
) -> None:
    """Log a session for a participant."""
    p = _load_or_exit(panel)
    pid = _resolve_or_exit(p, participant_id)
    try:
        resp = json.loads(responses)
    except json.JSONDecodeError:
        console.print("[red]--responses must be valid JSON[/red]")
        sys.exit(1)
    session = log_session(p, study_id, pid, resp, notes)
    save_panel(p, panel)
    if json_output:
        click.echo(json.dumps(session.to_dict()))
    else:
        console.print(f"[green]✓[/green] Session logged (ID: {session.id[:8]}…)")


# ---------------------------------------------------------------------------
# History & reporting
# ---------------------------------------------------------------------------

@cli.command("history")
@click.option("--panel", "-p", default="panel.json")
@click.argument("participant_id")
@click.option("--json-output", is_flag=True)
def history_cmd(panel: str, participant_id: str, json_output: bool) -> None:
    """Show full cross-study history for a participant."""
    p = _load_or_exit(panel)
    pid = _resolve_or_exit(p, participant_id)
    history = get_participant_history(p, pid)
    if json_output:
        click.echo(json.dumps(history))
        return
    pt = p.participants[pid]
    console.print(
        RichPanel(
            f"[bold]{pt.name}[/bold]\n"
            f"Archetype: {pt.archetype} · Segment: {pt.segment}\n"
            f"Versions: {pt.current_version} · Studies: {history['study_count']} "
            f"· Sessions: {history['session_count']}",
            title="Participant History",
        )
    )
    if pt.versions:
        console.print("\n[bold]Version timeline:[/bold]")
        for v in pt.versions:
            note_str = f"  — {v.note}" if v.note else ""
            console.print(f"  v{v.version}  {v.created_at[:10]}{note_str}")


@cli.command("diff")
@click.option("--panel", "-p", default="panel.json")
@click.argument("participant_id")
@click.option("--version-a", "-a", required=True, type=int, help="First version")
@click.option("--version-b", "-b", required=True, type=int, help="Second version")
@click.option("--json-output", is_flag=True)
def diff_cmd(
    panel: str,
    participant_id: str,
    version_a: int,
    version_b: int,
    json_output: bool,
) -> None:
    """Compare two versions of a participant."""
    p = _load_or_exit(panel)
    pid = _resolve_or_exit(p, participant_id)
    result = compare_participant_versions(p, pid, version_a, version_b)
    if json_output:
        click.echo(json.dumps(result))
        return
    if "error" in result:
        console.print(f"[red]{result['error']}[/red]")
        return
    console.print(
        RichPanel(
            f"[bold]{result['participant_name']}[/bold]  "
            f"v{version_a} → v{version_b}\n"
            f"Changed fields: {', '.join(result['changed_fields']) or 'none'}",
            title="Version Diff",
        )
    )
    for field, vals in result["diffs"].items():
        console.print(f"\n  [bold]{field}[/bold]")
        for label, val in vals.items():
            console.print(f"    {label}: {val}")


@cli.command("summary")
@click.option("--panel", "-p", default="panel.json")
@click.option("--json-output", is_flag=True)
def summary_cmd(panel: str, json_output: bool) -> None:
    """Show aggregate statistics for the panel."""
    p = _load_or_exit(panel)
    s = panel_summary(p)
    if json_output:
        click.echo(json.dumps(s))
        return
    console.print(
        RichPanel(
            f"[bold]{p.name}[/bold]\n{p.description or '—'}",
            title=f"Panel Summary — {s['participant_count']} participants",
        )
    )
    if s["archetypes"]:
        console.print("\n[bold]Archetypes:[/bold]")
        for arch, count in sorted(s["archetypes"].items(), key=lambda x: -x[1]):
            console.print(f"  {arch}: {count}")
    if s["segments"]:
        console.print("\n[bold]Segments:[/bold]")
        for seg, count in sorted(s["segments"].items(), key=lambda x: -x[1]):
            console.print(f"  {seg}: {count}")
    console.print(
        f"\nStudies: {s['study_count']} · "
        f"Sessions: {s['session_count']} · "
        f"Assignments: {s['assignment_count']}"
    )


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

@cli.command("export")
@click.option("--panel", "-p", default="panel.json")
@click.option(
    "--type",
    "export_type",
    type=click.Choice(["participants", "sessions", "assignments", "all"]),
    default="all",
    help="What to export",
)
@click.option("--output-dir", "-o", default=".", help="Output directory")
def export_cmd(panel: str, export_type: str, output_dir: str) -> None:
    """Export panel data to JSON files."""
    p = _load_or_exit(panel)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    if export_type in ("participants", "all"):
        dest = out / "participants.json"
        export_participants(p, dest)
        console.print(f"[green]✓[/green] Participants → {dest}")
    if export_type in ("sessions", "all"):
        dest = out / "sessions.json"
        export_sessions(p, dest)
        console.print(f"[green]✓[/green] Sessions → {dest}")
    if export_type in ("assignments", "all"):
        dest = out / "assignments.json"
        export_assignments(p, dest)
        console.print(f"[green]✓[/green] Assignments → {dest}")


if __name__ == "__main__":
    cli()


# ---------------------------------------------------------------------------
# LLM enrichment commands
# ---------------------------------------------------------------------------

@cli.command("evolve")
@click.option("--panel", "-p", default="panel.json")
@click.argument("participant_id")
@click.option("--study-context", required=True, help="What changed between waves")
@click.option("--llm-backend", type=click.Choice(["openai", "anthropic", "gemini"]), required=True)
@click.option("--apply", is_flag=True, help="Apply suggested updates as a new participant version")
@click.option("--json-output", is_flag=True)
def evolve_cmd(
    panel: str,
    participant_id: str,
    study_context: str,
    llm_backend: str,
    apply: bool,
    json_output: bool,
) -> None:
    """Suggest attribute drift for a participant via LLM enrichment.

    Analyses session history and suggests how attributes might plausibly
    evolve for the next study wave. Use --apply to write a new version.

    Requires: pip install "synthetic-panel[llm]"
    """
    try:
        from .llm import configure_backend, suggest_drift
    except ImportError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)

    p = _load_or_exit(panel)
    pid = _resolve_or_exit(p, participant_id)
    participant = p.participants[pid]
    sessions = [s.to_dict() for s in p.sessions if s.participant_id == pid]

    try:
        configure_backend(llm_backend)
        suggestion = suggest_drift(participant.to_dict(), sessions, study_context)
    except Exception as exc:
        console.print(f"[red]LLM call failed: {exc}[/red]")
        sys.exit(1)

    if apply and suggestion.get("suggested_updates"):
        updates: dict[str, Any] = {}
        raw_updates = suggestion["suggested_updates"]
        if "attributes" in raw_updates:
            merged = dict(participant.attributes)
            merged.update(raw_updates["attributes"])
            updates["attributes"] = merged
        for field in ("archetype", "segment", "tags"):
            if field in raw_updates:
                updates[field] = raw_updates[field]
        if updates:
            note = suggestion.get("version_note", f"LLM drift — {study_context}")
            update_participant(p, pid, updates, note)
            save_panel(p, panel)

    if json_output:
        out: dict[str, Any] = {"participant_id": pid, "suggestion": suggestion}
        if apply:
            out["applied"] = bool(suggestion.get("suggested_updates"))
            out["new_version"] = participant.current_version
        click.echo(json.dumps(out))
    else:
        updates_text = "\n".join(
            f"  {k}: {v}" for k, v in suggestion.get("suggested_updates", {}).items()
        ) or "  (none)"
        console.print(
            RichPanel(
                f"[bold]{participant.name}[/bold] — drift via {llm_backend}\n\n"
                f"[bold]Rationale:[/bold] {suggestion.get('drift_rationale', '—')}\n\n"
                f"[bold]Suggested updates:[/bold]\n{updates_text}",
                title="LLM Drift Suggestion",
            )
        )
        if suggestion.get("stability_notes"):
            console.print(f"\n[dim]Stability: {suggestion['stability_notes']}[/dim]")
        if apply and suggestion.get("suggested_updates"):
            console.print(
                f"\n[green]✓[/green] Applied → {participant.name} v{participant.current_version}"
            )
        elif apply:
            console.print("\n[yellow]No updates to apply.[/yellow]")


@cli.command("generate")
@click.option("--panel", "-p", default="panel.json")
@click.option("--archetype", required=True, help="Participant archetype label")
@click.option("--segment", required=True, help="Market or demographic segment")
@click.option("--study-context", required=True, help="Product or research area description")
@click.option("--llm-backend", type=click.Choice(["openai", "anthropic", "gemini"]), required=True)
@click.option("--add-to-panel", is_flag=True, help="Add generated participant to the panel")
@click.option("--json-output", is_flag=True)
def generate_cmd(
    panel: str,
    archetype: str,
    segment: str,
    study_context: str,
    llm_backend: str,
    add_to_panel: bool,
    json_output: bool,
) -> None:
    """Generate a richly profiled synthetic participant via LLM enrichment.

    Requires: pip install "synthetic-panel[llm]"
    """
    try:
        from .llm import configure_backend, generate_profile
    except ImportError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)

    try:
        configure_backend(llm_backend)
        profile = generate_profile(archetype, segment, study_context)
    except Exception as exc:
        console.print(f"[red]LLM call failed: {exc}[/red]")
        sys.exit(1)

    if add_to_panel:
        p = _load_or_exit(panel)
        participant = add_participant(
            p,
            name=profile.get("name", f"Synthetic {archetype}"),
            archetype=archetype,
            segment=segment,
            attributes=profile.get("attributes", {}),
            tags=profile.get("tags", []),
            note=f"LLM-generated — {llm_backend}",
        )
        save_panel(p, panel)
        profile["participant_id"] = participant.id

    if json_output:
        click.echo(json.dumps(profile))
    else:
        attrs_text = "\n".join(
            f"  {k}: {v}" for k, v in profile.get("attributes", {}).items()
        ) or "  (none)"
        console.print(
            RichPanel(
                f"[bold]{profile.get('name', '—')}[/bold]\n"
                f"Archetype: {archetype} · Segment: {segment}\n\n"
                f"[bold]Attributes:[/bold]\n{attrs_text}",
                title=f"Generated Profile — {llm_backend}",
            )
        )
        if profile.get("generation_rationale"):
            console.print(f"\n[dim]{profile['generation_rationale']}[/dim]")
        if add_to_panel and "participant_id" in profile:
            console.print(
                f"\n[green]✓[/green] Added to panel (ID: {profile['participant_id'][:8]}…)"
            )

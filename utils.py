"""
Utilities for the Pion Discovery tool: JSON parsing, cheat sheet markdown rendering.
"""

import json
import re
from typing import Optional


def parse_json_object(text: str) -> Optional[dict]:
    """
    Extract the first valid JSON object from arbitrary LLM text.
    Handles markdown code fences, preambles, and trailing commentary.
    """
    if not text:
        return None

    # Strip common code fences
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = cleaned.replace("```", "")

    # Find the first balanced { ... } block
    start = cleaned.find("{")
    if start < 0:
        return None

    depth = 0
    in_string = False
    escape = False
    for i, ch in enumerate(cleaned[start:], start=start):
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = cleaned[start : i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    # Try a more permissive cleanup pass — strip trailing commas
                    candidate2 = re.sub(r",(\s*[}\]])", r"\1", candidate)
                    try:
                        return json.loads(candidate2)
                    except json.JSONDecodeError:
                        return None
    return None


def render_cheatsheet_markdown(
    cs: dict,
    company: str,
    person_name: str,
    person_title: str,
    plain: bool = False,
) -> str:
    """
    Render the cheat sheet JSON as readable markdown.
    `plain=True` produces a download-friendly version without HTML span styling.
    """
    if not cs:
        return "_Cheat sheet generation returned no content._"

    lines = []

    # ── Headline ──────────────────────────────────────────────────────────────
    headline = cs.get("headline", "")
    if not plain:
        lines.append(f"<div class='section-label'>The Call</div>")
    else:
        lines.append("## The Call\n")
    lines.append(f"**{company} — {person_name}, {person_title}**\n")
    if headline:
        lines.append(f"> {headline}\n")

    # ── Person dossier ────────────────────────────────────────────────────────
    pd = cs.get("person_dossier", {}) or {}
    if not plain:
        lines.append(f"<div class='section-label'>Person Dossier</div>")
    else:
        lines.append("\n## Person Dossier\n")
    if pd.get("summary"):
        lines.append(pd["summary"] + "\n")
    if pd.get("key_facts"):
        for fact in pd["key_facts"]:
            lines.append(f"- {fact}")
        lines.append("")
    if pd.get("what_changes_about_the_call"):
        lines.append(f"**What changes about this call:** {pd['what_changes_about_the_call']}\n")

    # ── Company snapshot ──────────────────────────────────────────────────────
    co = cs.get("company_snapshot", {}) or {}
    if not plain:
        lines.append(f"<div class='section-label'>Company Snapshot</div>")
    else:
        lines.append("\n## Company Snapshot\n")
    if co.get("summary"):
        lines.append(co["summary"] + "\n")
    if co.get("recommended_pion_product"):
        lines.append(f"**Lead with:** {co['recommended_pion_product']}")
    if co.get("rationale"):
        lines.append(f"**Why:** {co['rationale']}")
    if co.get("displacement_target"):
        lines.append(f"**Displace:** {co['displacement_target']}")
    lines.append("")

    # ── Hypotheses ────────────────────────────────────────────────────────────
    if not plain:
        lines.append(f"<div class='section-label'>Walk In Believing</div>")
    else:
        lines.append("\n## Walk In Believing (Hypotheses)\n")
    for h in cs.get("hypotheses", []) or []:
        lines.append(f"- {h}")
    lines.append("")

    # ── Discovery questions ───────────────────────────────────────────────────
    qs = cs.get("discovery_questions", {}) or {}
    if not plain:
        lines.append(f"<div class='section-label'>Discovery Questions</div>")
    else:
        lines.append("\n## Discovery Questions\n")
    for stage, label in [
        ("situation", "Situation"),
        ("pain", "Pain"),
        ("impact", "Impact"),
        ("vision", "Vision"),
    ]:
        questions = qs.get(stage, []) or []
        if not questions:
            continue
        lines.append(f"**{label}**")
        for q in questions:
            lines.append(f"- {q}")
        lines.append("")

    # ── Listen for ────────────────────────────────────────────────────────────
    if not plain:
        lines.append(f"<div class='section-label'>Listen For (mid-call pivots)</div>")
    else:
        lines.append("\n## Listen For\n")
    for item in cs.get("listen_for", []) or []:
        sig = item.get("signal", "")
        unlocks = item.get("what_it_unlocks", "")
        lines.append(f"- *\"{sig}\"* → {unlocks}")
    lines.append("")

    # ── Landmines ─────────────────────────────────────────────────────────────
    if not plain:
        lines.append(f"<div class='section-label'>Landmines</div>")
    else:
        lines.append("\n## Landmines\n")
    for lm in cs.get("landmines", []) or []:
        lines.append(f"- ⚠️ {lm}")
    lines.append("")

    # ── Proof points ──────────────────────────────────────────────────────────
    if not plain:
        lines.append(f"<div class='section-label'>Proof Points to Load</div>")
    else:
        lines.append("\n## Proof Points to Load\n")
    for pp in cs.get("proof_points_to_load", []) or []:
        point = pp.get("point", "")
        when = pp.get("use_when", "")
        lines.append(f"- **{point}** — *use when:* {when}")
    lines.append("")

    # ── Opening line ──────────────────────────────────────────────────────────
    if cs.get("opening_line"):
        if not plain:
            lines.append(f"<div class='section-label'>Opening Line</div>")
        else:
            lines.append("\n## Opening Line\n")
        lines.append(f"> {cs['opening_line']}\n")

    # ── Ideal next step ───────────────────────────────────────────────────────
    if cs.get("ideal_next_step"):
        if not plain:
            lines.append(f"<div class='section-label'>Ideal Next Step</div>")
        else:
            lines.append("\n## Ideal Next Step\n")
        lines.append(cs["ideal_next_step"])

    return "\n".join(lines)

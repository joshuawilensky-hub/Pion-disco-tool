"""
Utilities for Pion Disco Prep: JSON parsing + Disco Prep markdown rendering.
"""

import json
import re
from typing import Optional


def parse_json_object(text: str) -> Optional[dict]:
    """Extract the first valid JSON object from arbitrary LLM text."""
    if not text:
        return None

    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = cleaned.replace("```", "")

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
                    candidate2 = re.sub(r",(\s*[}\]])", r"\1", candidate)
                    try:
                        return json.loads(candidate2)
                    except json.JSONDecodeError:
                        return None
    return None


def render_disco_prep_markdown(
    prep: dict,
    company: str,
    person_name: str,
    person_title: str,
    plain: bool = False,
) -> str:
    """Render the Disco Prep JSON as readable markdown."""
    if not prep:
        return "_No content generated._"

    L = []
    label = (lambda txt: L.append(f"<div class='section-label'>{txt}</div>")) if not plain else (lambda txt: L.append(f"\n## {txt}\n"))

    # ── Headline ──────────────────────────────────────────────────────────────
    label("The Call")
    L.append(f"**{company} — {person_name}, {person_title}**\n")
    if prep.get("headline"):
        L.append(f"> {prep['headline']}\n")

    # ── Person dossier ────────────────────────────────────────────────────────
    pd = prep.get("person_dossier", {}) or {}

    label("Person")
    if pd.get("summary"):
        L.append(pd["summary"] + "\n")

    # Title-driven priorities — most important section
    if pd.get("title_driven_priorities"):
        L.append("**What they're measured on:**")
        for p in pd["title_driven_priorities"]:
            L.append(f"- {p}")
        L.append("")

    # Rapport moments
    rapport = pd.get("rapport_moments") or []
    if rapport:
        label("Rapport Moments")
        for rm in rapport:
            moment = rm.get("moment", "")
            how = rm.get("how_to_use", "")
            L.append(f"- **{moment}**")
            if how:
                L.append(f"  ↳ *{how}*")
        L.append("")

    if pd.get("what_changes_about_the_call"):
        L.append(f"**What changes about this call:** {pd['what_changes_about_the_call']}\n")

    # ── Company snapshot ──────────────────────────────────────────────────────
    co = prep.get("company_snapshot", {}) or {}
    label("Company Snapshot")
    if co.get("summary"):
        L.append(co["summary"] + "\n")
    if co.get("recommended_pion_product"):
        L.append(f"**Lead with:** {co['recommended_pion_product']}")
    if co.get("rationale"):
        L.append(f"**Why:** {co['rationale']}")
    if co.get("displacement_target"):
        L.append(f"**Displace:** {co['displacement_target']}")
    L.append("")

    # ── Hypotheses ────────────────────────────────────────────────────────────
    if prep.get("hypotheses"):
        label("Walk In Believing")
        for h in prep["hypotheses"]:
            L.append(f"- {h}")
        L.append("")

    # ── Discovery questions ───────────────────────────────────────────────────
    qs = prep.get("discovery_questions", {}) or {}
    if any(qs.get(k) for k in ["situation", "pain", "impact", "vision"]):
        label("Discovery Questions")
        for stage, heading in [("situation", "Situation"), ("pain", "Pain"), ("impact", "Impact"), ("vision", "Vision")]:
            qlist = qs.get(stage, []) or []
            if not qlist:
                continue
            L.append(f"**{heading}**")
            for q in qlist:
                L.append(f"- {q}")
            L.append("")

    # ── Listen for ────────────────────────────────────────────────────────────
    if prep.get("listen_for"):
        label("Listen For (mid-call pivots)")
        for item in prep["listen_for"]:
            sig = item.get("signal", "")
            unlocks = item.get("what_it_unlocks", "")
            L.append(f"- *\"{sig}\"* → {unlocks}")
        L.append("")

    # ── Landmines ─────────────────────────────────────────────────────────────
    if prep.get("landmines"):
        label("Landmines")
        for lm in prep["landmines"]:
            L.append(f"- ⚠️ {lm}")
        L.append("")

    # ── Proof points ──────────────────────────────────────────────────────────
    if prep.get("proof_points_to_load"):
        label("Proof Points to Load")
        for pp in prep["proof_points_to_load"]:
            point = pp.get("point", "")
            when = pp.get("use_when", "")
            L.append(f"- **{point}** — *use when:* {when}")
        L.append("")

    # ── Opening line ──────────────────────────────────────────────────────────
    if prep.get("opening_line"):
        label("Opening Line")
        L.append(f"> {prep['opening_line']}\n")

    # ── Ideal next step ───────────────────────────────────────────────────────
    if prep.get("ideal_next_step"):
        label("Ideal Next Step")
        L.append(prep["ideal_next_step"])

    return "\n".join(L)

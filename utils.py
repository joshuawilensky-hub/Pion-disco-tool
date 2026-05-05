"""
Utilities for Pion Disco Prep: JSON parsing + Disco Prep markdown rendering.

Renderer outputs sections in the order the rep will use them:
  1. Headline / Person / Company snapshot
  2. Opening Line (rapport)
  3. Menu of Pain (3 options with pain funnels)
  4. CHAMP qualifiers (back-third of call)
  5. Listen-for signals (mid-call pivots)
  6. Landmines
  7. Four-Quadrant Hypothesis (pre-call pitch hypothesis)
  8. Proof points + Ideal next step
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
    if pd.get("title_driven_priorities"):
        L.append("**What they're measured on:**")
        for p in pd["title_driven_priorities"]:
            L.append(f"- {p}")
        L.append("")

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

    # ── Opening line ──────────────────────────────────────────────────────────
    if prep.get("opening_line"):
        label("Opening Line")
        L.append(f"> {prep['opening_line']}\n")

    # ── Menu of Pain ──────────────────────────────────────────────────────────
    menu = prep.get("menu_of_pain", {}) or {}
    if menu:
        label("Menu of Pain — Your Opening Probe")
        if menu.get("intro_script"):
            L.append(f"**Script:** *\"{menu['intro_script']}\"*\n")

        for opt in menu.get("options", []) or []:
            lbl = opt.get("label", "?")
            pain = opt.get("pain_in_customer_language", "")
            mapped = opt.get("which_pion_pain_this_maps_to", "")
            pivot = opt.get("if_they_pick_this_pivot_to", "")
            L.append(f"#### Option {lbl}: {pain}")
            if mapped:
                L.append(f"*Maps to Pion pain: {mapped}* · *Pivot to: {pivot}*\n")

            funnel = opt.get("pain_funnel", {}) or {}
            if funnel.get("problem_question"):
                L.append(f"**Problem:** {funnel['problem_question']}")
            for q in funnel.get("implication_questions", []) or []:
                L.append(f"**Implication:** {q}")
            if funnel.get("need_payoff_question"):
                L.append(f"**Need-Payoff:** {funnel['need_payoff_question']}")
            L.append("")

    # ── CHAMP qualifiers ──────────────────────────────────────────────────────
    champ = prep.get("champ_qualifiers", {}) or {}
    if champ:
        label("CHAMP Qualifiers — Back Third of Call")
        if champ.get("challenges_confirm"):
            L.append(f"**Challenges:** {champ['challenges_confirm']}")
        if champ.get("authority"):
            L.append(f"**Authority:** {champ['authority']}")
        if champ.get("money"):
            L.append(f"**Money:** {champ['money']}")
        if champ.get("prioritization"):
            L.append(f"**Prioritization:** {champ['prioritization']}")
        L.append("")

    # ── Listen for ────────────────────────────────────────────────────────────
    if prep.get("listen_for"):
        label("Listen For — Mid-Call Pivots")
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

    # ── Four-quadrant hypothesis ──────────────────────────────────────────────
    fq = prep.get("four_quadrant_hypothesis", {}) or {}
    if fq:
        label("Four-Quadrant Pitch Hypothesis")
        L.append("*Your pre-call bet on what the partnership pitch will look like — discovery validates or invalidates.*\n")

        if fq.get("strategic_growth_objectives"):
            L.append("**1. Strategic Growth Objectives** *(what you suspect they're chasing)*")
            for o in fq["strategic_growth_objectives"]:
                L.append(f"- {o}")
            L.append("")

        if fq.get("current_challenge_and_impact"):
            L.append("**2. Current Challenge & Impact** *(what you suspect is hurting)*")
            for c in fq["current_challenge_and_impact"]:
                L.append(f"- {c}")
            L.append("")

        if fq.get("how_we_solve_this"):
            L.append("**3. How We Solve This** *(your Pion product hypothesis)*")
            for h in fq["how_we_solve_this"]:
                L.append(f"- {h}")
            L.append("")

        if fq.get("expected_business_outcome"):
            L.append("**4. Expected Business Outcome** *(proof-anchored)*")
            L.append(f"- {fq['expected_business_outcome']}")
            L.append("")

    # ── Proof points ──────────────────────────────────────────────────────────
    if prep.get("proof_points_to_load"):
        label("Proof Points to Load")
        for pp in prep["proof_points_to_load"]:
            point = pp.get("point", "")
            when = pp.get("use_when", "")
            L.append(f"- **{point}** — *use when:* {when}")
        L.append("")

    # ── Ideal next step ───────────────────────────────────────────────────────
    if prep.get("ideal_next_step"):
        label("Ideal Next Step")
        L.append(prep["ideal_next_step"])

    return "\n".join(L)

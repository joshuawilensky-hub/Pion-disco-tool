"""
Pion Discovery Cheat Sheet
==========================
A pre-call discovery prep tool for Pion Business Development Managers.

Inputs:
  - Company being sold to (e.g. Chipotle)
  - Person on the call (full name)
  - Their exact title
  - Pion product angle to lead with (or let the tool decide)

Pipeline:
  1) Live person search (LinkedIn footprint, podcasts, press mentions, tenure)
  2) Live company signal pull (UNiDAYS/SheerID presence, loyalty app status, promo cadence)
  3) Synthesis into a one-page discovery cheat sheet:
       - Person dossier
       - Company snapshot
       - Hypothesised pain (specific to this person, not generic)
       - Discovery question bank (Situation -> Pain -> Impact -> Vision)
       - Listen-for signals tied to Pion product pivots
       - Landmines specific to this profile
       - Proof points to load before the call

Provider waterfall: Perplexity -> Anthropic -> OpenAI -> Gemini
  - Person & company search default to Perplexity (live, cited, cheap)
  - Synthesis defaults to Anthropic (best reasoning over messy inputs)
  - Each step falls through the waterfall if its primary provider fails
"""

import streamlit as st
import json
from datetime import datetime

from prompts import (
    PERSON_RESEARCH_PROMPT,
    COMPANY_RESEARCH_PROMPT,
    SYNTHESIS_SYSTEM_PROMPT,
    build_synthesis_user_prompt,
)
from providers import call_with_search, call_for_synthesis
from utils import parse_json_object, render_cheatsheet_markdown

# ── Page setup ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Pion Disco Tool",
    page_icon="🎯",
    layout="wide",
)

# Editorial / utility aesthetic — deliberate restraint, strong type hierarchy
st.markdown(
    """
    <style>
      /* Typography */
      @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,800&family=JetBrains+Mono:wght@400;600&family=Inter+Tight:wght@400;500;600&display=swap');

      html, body, [class*="css"] {
        font-family: 'Inter Tight', sans-serif;
      }
      h1, h2, h3 { font-family: 'Fraunces', serif; letter-spacing: -0.02em; }
      h1 { font-weight: 800; }
      code, pre { font-family: 'JetBrains Mono', monospace; }

      /* Headline rule */
      .pion-hero {
        border-bottom: 3px solid #0F172A;
        padding-bottom: 0.75rem;
        margin-bottom: 1.5rem;
      }
      .pion-hero h1 { margin: 0; font-size: 2.4rem; }
      .pion-hero .kicker {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: #64748B;
      }

      /* Section labels in cheat sheet */
      .section-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: #64748B;
        margin-top: 1.25rem;
        margin-bottom: 0.4rem;
      }

      /* Cheatsheet card */
      .cheatsheet {
        background: #FAFAF7;
        border: 1px solid #E5E5DF;
        border-left: 4px solid #0F172A;
        padding: 1.5rem 1.75rem;
        border-radius: 4px;
      }

      /* Provider chip */
      .chip {
        display: inline-block;
        padding: 2px 8px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        background: #0F172A;
        color: #FAFAF7;
        border-radius: 2px;
        margin-right: 6px;
      }
      .chip.muted {
        background: #E5E5DF;
        color: #64748B;
      }

      /* Tighten Streamlit defaults */
      .block-container { padding-top: 2rem; max-width: 1100px; }
      [data-testid="stSidebar"] { background: #FAFAF7; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Sidebar: provider keys & waterfall config ────────────────────────────────
st.sidebar.markdown("### ⚙️ Provider Keys")
st.sidebar.caption("Waterfall: Perplexity → Anthropic → OpenAI → Gemini")

api_keys = {
    "perplexity": st.sidebar.text_input("Perplexity API key", type="password", key="pplx"),
    "anthropic": st.sidebar.text_input("Anthropic API key", type="password", key="anth"),
    "openai": st.sidebar.text_input("OpenAI API key", type="password", key="oai"),
    "gemini": st.sidebar.text_input("Gemini API key", type="password", key="gem"),
}

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔬 Search step")
search_primary = st.sidebar.selectbox(
    "Primary provider for live web research",
    ["perplexity", "anthropic", "openai", "gemini"],
    index=0,
    help="Perplexity is recommended — purpose-built for live cited search, cheapest.",
)

st.sidebar.markdown("### ✍️ Synthesis step")
synth_primary = st.sidebar.selectbox(
    "Primary provider for cheat-sheet synthesis",
    ["anthropic", "openai", "gemini", "perplexity"],
    index=0,
    help="Anthropic is recommended — best reasoning over messy multi-source inputs.",
)


# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="pion-hero">
      <div class="kicker">Pion · Business Development</div>
      <h1>Discovery Cheat Sheet</h1>
    </div>
    """,
    unsafe_allow_html=True,
)
st.caption(
    "Pre-call prep for booked discovery meetings. Enter the company, the person, and their title — "
    "the tool pulls live signal on both, then synthesises a one-page cheat sheet you scan in 90 seconds before the call."
)


# ── Inputs ────────────────────────────────────────────────────────────────────
with st.form("discovery_form"):
    col1, col2 = st.columns([1, 1])
    with col1:
        company = st.text_input(
            "Company",
            placeholder="e.g. Chipotle Mexican Grill",
            help="The brand you're pitching to.",
        )
        person_name = st.text_input(
            "Person on the call",
            placeholder="e.g. Stephanie Perdue",
            help="Full name as it appears on LinkedIn.",
        )
    with col2:
        person_title = st.text_input(
            "Their exact title",
            placeholder="e.g. VP, Brand Marketing",
            help="Use the title from the calendar invite or LinkedIn.",
        )
        product_angle = st.selectbox(
            "Pion product angle",
            [
                "Let the tool decide based on signal",
                "Verification (Connect / Beans ID core)",
                "Loyalty SSO (Playbook 3)",
                "Media",
                "BeansID multi-group",
            ],
            help="If you already know which product makes sense, pick it. Otherwise the tool will recommend based on company signal.",
        )

    extra_context = st.text_area(
        "Anything else worth knowing? (optional)",
        placeholder="e.g. They've already seen a deck. We were introduced by Robbie. Their CMO just left.",
        height=80,
    )

    submitted = st.form_submit_button("🎯 Build cheat sheet", type="primary", use_container_width=True)


# ── Run pipeline ──────────────────────────────────────────────────────────────
if submitted:
    # Validate inputs
    missing = []
    if not company.strip(): missing.append("company")
    if not person_name.strip(): missing.append("person name")
    if not person_title.strip(): missing.append("person title")
    if missing:
        st.error(f"Missing: {', '.join(missing)}")
        st.stop()

    # Validate that the primary search/synth providers have keys
    if not api_keys.get(search_primary):
        st.error(f"No API key for the search provider you selected ({search_primary}). Add it in the sidebar.")
        st.stop()
    if not api_keys.get(synth_primary):
        st.error(f"No API key for the synthesis provider you selected ({synth_primary}). Add it in the sidebar.")
        st.stop()

    progress = st.progress(0, text="Starting…")

    # ── Step 1: person research ───────────────────────────────────────────────
    progress.progress(10, text=f"Researching {person_name} via {search_primary}…")
    person_prompt = PERSON_RESEARCH_PROMPT.format(
        person_name=person_name.strip(),
        person_title=person_title.strip(),
        company=company.strip(),
    )
    person_raw, person_provider_used = call_with_search(
        prompt=person_prompt,
        api_keys=api_keys,
        primary=search_primary,
    )
    person_data = parse_json_object(person_raw) if person_raw else {}
    progress.progress(40, text=f"Researching {company} via {search_primary}…")

    # ── Step 2: company research ──────────────────────────────────────────────
    company_prompt = COMPANY_RESEARCH_PROMPT.format(company=company.strip())
    company_raw, company_provider_used = call_with_search(
        prompt=company_prompt,
        api_keys=api_keys,
        primary=search_primary,
    )
    company_data = parse_json_object(company_raw) if company_raw else {}
    progress.progress(70, text=f"Synthesising cheat sheet via {synth_primary}…")

    # ── Step 3: synthesis ─────────────────────────────────────────────────────
    synth_user_prompt = build_synthesis_user_prompt(
        company=company.strip(),
        person_name=person_name.strip(),
        person_title=person_title.strip(),
        product_angle=product_angle,
        extra_context=extra_context.strip(),
        person_data=person_data,
        company_data=company_data,
    )
    cheatsheet_raw, synth_provider_used = call_for_synthesis(
        system_prompt=SYNTHESIS_SYSTEM_PROMPT,
        user_prompt=synth_user_prompt,
        api_keys=api_keys,
        primary=synth_primary,
    )
    cheatsheet = parse_json_object(cheatsheet_raw) if cheatsheet_raw else {}

    progress.progress(100, text="Done.")
    progress.empty()

    if not cheatsheet:
        st.error("Synthesis failed — couldn't parse cheat sheet output. Try a different synthesis provider.")
        with st.expander("Debug: raw outputs"):
            st.text("Person raw:"); st.code(person_raw or "(empty)")
            st.text("Company raw:"); st.code(company_raw or "(empty)")
            st.text("Cheatsheet raw:"); st.code(cheatsheet_raw or "(empty)")
        st.stop()

    # ── Render cheat sheet ────────────────────────────────────────────────────
    st.markdown("### Your Cheat Sheet")
    st.markdown(
        f"<span class='chip'>Person · {person_provider_used}</span>"
        f"<span class='chip'>Company · {company_provider_used}</span>"
        f"<span class='chip'>Synthesis · {synth_provider_used}</span>",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="cheatsheet">', unsafe_allow_html=True)
    st.markdown(render_cheatsheet_markdown(cheatsheet, company, person_name, person_title), unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Downloads ─────────────────────────────────────────────────────────────
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    safe_company = company.replace(" ", "_").replace("/", "_")
    safe_person = person_name.replace(" ", "_")
    base_name = f"pion_discovery_{safe_company}_{safe_person}_{timestamp}"

    md_export = render_cheatsheet_markdown(cheatsheet, company, person_name, person_title, plain=True)
    full_payload = {
        "generated_at": datetime.now().isoformat(),
        "inputs": {
            "company": company,
            "person_name": person_name,
            "person_title": person_title,
            "product_angle": product_angle,
            "extra_context": extra_context,
        },
        "providers_used": {
            "person_search": person_provider_used,
            "company_search": company_provider_used,
            "synthesis": synth_provider_used,
        },
        "person_data": person_data,
        "company_data": company_data,
        "cheatsheet": cheatsheet,
    }

    col_dl1, col_dl2 = st.columns(2)
    col_dl1.download_button(
        "📄 Download cheat sheet (.md)",
        data=md_export,
        file_name=f"{base_name}.md",
        mime="text/markdown",
        use_container_width=True,
    )
    col_dl2.download_button(
        "🗂️ Download full research bundle (.json)",
        data=json.dumps(full_payload, indent=2),
        file_name=f"{base_name}.json",
        mime="application/json",
        use_container_width=True,
    )

    # Raw research expanders
    with st.expander("🔍 Raw person research"):
        st.json(person_data or {"_raw": person_raw})
    with st.expander("🏢 Raw company research"):
        st.json(company_data or {"_raw": company_raw})

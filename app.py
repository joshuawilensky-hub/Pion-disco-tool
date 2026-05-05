"""
Pion Disco Prep
===============
Pre-call discovery prep for Pion Business Development Managers.

Phased flow:
  Phase 1 — Inputs:      You enter company, person, title
  Phase 2 — Review:      You see and edit the live research dossiers
  Phase 3 — Disco Prep:  Synthesis produces a one-page brief tuned to
                          title-driven priorities and rapport-relevant moments

API keys are read from st.secrets — no UI fields. Configure them in Streamlit Cloud
under Settings → Secrets in TOML format. Any subset works:

  PERPLEXITY_API_KEY = "pplx-..."
  ANTHROPIC_API_KEY  = "sk-ant-..."
  OPENAI_API_KEY     = "sk-..."
  GEMINI_API_KEY     = "..."
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
from providers import call_search, call_synthesis, available_providers
from utils import parse_json_object, render_disco_prep_markdown


# ── Page setup ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Pion Disco Prep",
    page_icon="🎯",
    layout="wide",
)

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,800&family=JetBrains+Mono:wght@400;600&family=Inter+Tight:wght@400;500;600&display=swap');

      html, body, [class*="css"] { font-family: 'Inter Tight', sans-serif; }
      h1, h2, h3 { font-family: 'Fraunces', serif; letter-spacing: -0.02em; }
      h1 { font-weight: 800; }
      code, pre { font-family: 'JetBrains Mono', monospace; }

      .block-container { padding-top: 3rem; max-width: 1100px; }
      [data-testid="stSidebar"] { background: #FAFAF7; }

      .pion-hero {
        border-bottom: 3px solid #0F172A;
        padding-bottom: 0.75rem;
        margin-bottom: 1.5rem;
        margin-top: 0.5rem;
      }
      .pion-hero h1 { margin: 0; font-size: 2.4rem; }
      .pion-hero .kicker {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: #64748B;
        margin-bottom: 0.4rem;
      }

      .section-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: #64748B;
        margin-top: 1.25rem;
        margin-bottom: 0.4rem;
      }

      .disco-prep {
        background: #FAFAF7;
        border: 1px solid #E5E5DF;
        border-left: 4px solid #0F172A;
        padding: 1.5rem 1.75rem;
        border-radius: 4px;
      }

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
      .chip.muted { background: #E5E5DF; color: #64748B; }

      .phase-pill {
        display: inline-block;
        padding: 4px 10px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        background: #FEF3C7;
        color: #78350F;
        border-radius: 99px;
        margin-bottom: 1rem;
      }
      .phase-pill.done { background: #D1FAE5; color: #065F46; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Resolve providers from st.secrets ─────────────────────────────────────────
def get_secret(key: str) -> str:
    try:
        return st.secrets.get(key, "") or ""
    except Exception:
        return ""

api_keys = {
    "perplexity": get_secret("PERPLEXITY_API_KEY"),
    "anthropic":  get_secret("ANTHROPIC_API_KEY"),
    "openai":     get_secret("OPENAI_API_KEY"),
    "gemini":     get_secret("GEMINI_API_KEY"),
}
providers_with_keys = available_providers(api_keys)


# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.markdown("### ⚙️ Providers")

if not providers_with_keys:
    st.sidebar.error(
        "No API keys found in Streamlit secrets. Add at least one in Settings → Secrets:\n\n"
        "```toml\nANTHROPIC_API_KEY = \"sk-ant-...\"\n```"
    )
else:
    st.sidebar.success(f"Loaded: {', '.join(providers_with_keys)}")

st.sidebar.markdown("---")

search_default = "perplexity" if "perplexity" in providers_with_keys else (providers_with_keys[0] if providers_with_keys else None)
search_provider = st.sidebar.selectbox(
    "🔬 Search step provider",
    options=providers_with_keys or ["(no keys configured)"],
    index=providers_with_keys.index(search_default) if search_default else 0,
    help="Provider used for live web research on the company and person.",
    disabled=not providers_with_keys,
)

synth_default = "anthropic" if "anthropic" in providers_with_keys else (providers_with_keys[0] if providers_with_keys else None)
synth_provider = st.sidebar.selectbox(
    "✍️ Synthesis step provider",
    options=providers_with_keys or ["(no keys configured)"],
    index=providers_with_keys.index(synth_default) if synth_default else 0,
    help="Provider used to turn the dossiers into your Disco Prep.",
    disabled=not providers_with_keys,
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Recommended: Perplexity for search (cited live data, cheap), "
    "Anthropic for synthesis (best reasoning over messy inputs)."
)


# ── Session state init ────────────────────────────────────────────────────────
for key, default in [
    ("phase", "input"),
    ("person_data", {}),
    ("company_data", {}),
    ("company_cache", {}),
    ("disco_prep", {}),
    ("inputs", {}),
    ("providers_used", {}),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="pion-hero">
      <div class="kicker">Pion · Business Development</div>
      <h1>Disco Prep</h1>
    </div>
    """,
    unsafe_allow_html=True,
)
st.caption(
    "Pre-call prep for booked discovery meetings. Enter the company and who's on the call — "
    "the tool pulls live signal, lets you review and edit the dossiers, then generates a one-page Disco Prep "
    "tuned to title-driven priorities and rapport-relevant moments."
)


# ── PHASE 1 — INPUT ───────────────────────────────────────────────────────────
if st.session_state.phase == "input":
    st.markdown('<div class="phase-pill">Phase 1 of 3 · Inputs</div>', unsafe_allow_html=True)

    with st.form("inputs_form"):
        col1, col2 = st.columns([1, 1])
        with col1:
            company = st.text_input("Company", placeholder="e.g. Chipotle Mexican Grill")
            person_name = st.text_input("Person on the call", placeholder="e.g. Stephanie Perdue")
        with col2:
            person_title = st.text_input("Their exact title", placeholder="e.g. VP, Brand Marketing")
            product_angle = st.selectbox(
                "Pion product angle",
                [
                    "Let the tool decide based on signal",
                    "Verification (Connect / Beans ID core)",
                    "Loyalty SSO (Playbook 3)",
                    "Media",
                    "BeansID multi-group",
                ],
            )

        extra_context = st.text_area(
            "Anything else worth knowing? (optional)",
            placeholder="e.g. They've already seen a deck. Robbie introduced us. Their CMO just left.",
            height=80,
        )

        submitted = st.form_submit_button(
            "🔬 Run research",
            type="primary",
            use_container_width=True,
            disabled=not providers_with_keys,
        )

    if submitted:
        missing = []
        if not company.strip(): missing.append("company")
        if not person_name.strip(): missing.append("person name")
        if not person_title.strip(): missing.append("person title")
        if missing:
            st.error(f"Missing: {', '.join(missing)}")
            st.stop()

        st.session_state.inputs = {
            "company": company.strip(),
            "person_name": person_name.strip(),
            "person_title": person_title.strip(),
            "product_angle": product_angle,
            "extra_context": extra_context.strip(),
        }

        # Person research
        with st.spinner(f"Researching {person_name} via {search_provider}…"):
            person_prompt = PERSON_RESEARCH_PROMPT.format(
                person_name=person_name.strip(),
                person_title=person_title.strip(),
                company=company.strip(),
            )
            try:
                person_raw = call_search(prompt=person_prompt, api_keys=api_keys, provider=search_provider)
                st.session_state.person_data = parse_json_object(person_raw) if person_raw else {}
                st.session_state.providers_used["person_search"] = search_provider
            except Exception as e:
                st.error(f"Person research failed via {search_provider}: {e}")
                st.stop()

        # Company research with session cache
        company_key = company.strip().lower()
        if company_key in st.session_state.company_cache:
            st.info(f"Using cached company research for {company.strip()}.")
            cached = st.session_state.company_cache[company_key]
            st.session_state.company_data = cached["data"]
            st.session_state.providers_used["company_search"] = cached["provider"] + " (cached)"
        else:
            with st.spinner(f"Researching {company} via {search_provider}…"):
                company_prompt = COMPANY_RESEARCH_PROMPT.format(company=company.strip())
                try:
                    company_raw = call_search(prompt=company_prompt, api_keys=api_keys, provider=search_provider)
                    company_data = parse_json_object(company_raw) if company_raw else {}
                    st.session_state.company_data = company_data
                    st.session_state.company_cache[company_key] = {"data": company_data, "provider": search_provider}
                    st.session_state.providers_used["company_search"] = search_provider
                except Exception as e:
                    st.error(f"Company research failed via {search_provider}: {e}")
                    st.stop()

        st.session_state.phase = "research_done"
        st.rerun()


# ── PHASE 2 — REVIEW & EDIT ───────────────────────────────────────────────────
elif st.session_state.phase == "research_done":
    st.markdown('<div class="phase-pill done">Phase 2 of 3 · Review & edit dossiers</div>', unsafe_allow_html=True)

    inputs = st.session_state.inputs
    st.markdown(f"**{inputs['company']}** · {inputs['person_name']}, *{inputs['person_title']}*")
    st.caption(
        "Review the dossiers below — fix anything wrong, add anything missing. "
        "Synthesis runs on whatever you save here."
    )

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("##### 👤 Person dossier")
        st.caption(f"Source: {st.session_state.providers_used.get('person_search', 'unknown')}")
        person_json_str = st.text_area(
            "Edit JSON",
            value=json.dumps(st.session_state.person_data, indent=2) if st.session_state.person_data else "{}",
            height=420,
            key="person_editor",
        )

    with col_right:
        st.markdown("##### 🏢 Company dossier")
        st.caption(f"Source: {st.session_state.providers_used.get('company_search', 'unknown')}")
        company_json_str = st.text_area(
            "Edit JSON",
            value=json.dumps(st.session_state.company_data, indent=2) if st.session_state.company_data else "{}",
            height=420,
            key="company_editor",
        )

    col_a, _, col_c = st.columns([1, 1, 1])
    with col_a:
        if st.button("⬅ Back to inputs", use_container_width=True):
            st.session_state.phase = "input"
            st.rerun()
    with col_c:
        build = st.button("🎯 Build Disco Prep", type="primary", use_container_width=True)

    if build:
        try:
            edited_person = json.loads(person_json_str) if person_json_str.strip() else {}
            edited_company = json.loads(company_json_str) if company_json_str.strip() else {}
        except json.JSONDecodeError as e:
            st.error(f"JSON parse error in dossier edits: {e}")
            st.stop()

        st.session_state.person_data = edited_person
        st.session_state.company_data = edited_company

        with st.spinner(f"Synthesising Disco Prep via {synth_provider}…"):
            synth_user = build_synthesis_user_prompt(
                company=inputs["company"],
                person_name=inputs["person_name"],
                person_title=inputs["person_title"],
                product_angle=inputs["product_angle"],
                extra_context=inputs["extra_context"],
                person_data=edited_person,
                company_data=edited_company,
            )
            try:
                prep_raw = call_synthesis(
                    system_prompt=SYNTHESIS_SYSTEM_PROMPT,
                    user_prompt=synth_user,
                    api_keys=api_keys,
                    provider=synth_provider,
                )
                disco_prep = parse_json_object(prep_raw) if prep_raw else {}
            except Exception as e:
                st.error(f"Synthesis failed via {synth_provider}: {e}")
                st.stop()

            if not disco_prep:
                st.error("Synthesis returned no valid output. Try a different synthesis provider.")
                with st.expander("Debug: raw output"):
                    st.code(prep_raw or "(empty)")
                st.stop()

            st.session_state.disco_prep = disco_prep
            st.session_state.providers_used["synthesis"] = synth_provider
            st.session_state.phase = "prep_done"
            st.rerun()


# ── PHASE 3 — DISCO PREP RENDERED ─────────────────────────────────────────────
elif st.session_state.phase == "prep_done":
    st.markdown('<div class="phase-pill done">Phase 3 of 3 · Disco Prep ready</div>', unsafe_allow_html=True)

    inputs = st.session_state.inputs
    prep = st.session_state.disco_prep
    used = st.session_state.providers_used

    st.markdown(
        f"<span class='chip'>Person · {used.get('person_search', '?')}</span>"
        f"<span class='chip'>Company · {used.get('company_search', '?')}</span>"
        f"<span class='chip'>Synthesis · {used.get('synthesis', '?')}</span>",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="disco-prep">', unsafe_allow_html=True)
    st.markdown(
        render_disco_prep_markdown(prep, inputs["company"], inputs["person_name"], inputs["person_title"]),
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    safe_company = inputs["company"].replace(" ", "_").replace("/", "_")
    safe_person = inputs["person_name"].replace(" ", "_")
    base_name = f"pion_disco_prep_{safe_company}_{safe_person}_{timestamp}"

    md_export = render_disco_prep_markdown(prep, inputs["company"], inputs["person_name"], inputs["person_title"], plain=True)
    full_payload = {
        "generated_at": datetime.now().isoformat(),
        "inputs": inputs,
        "providers_used": used,
        "person_data": st.session_state.person_data,
        "company_data": st.session_state.company_data,
        "disco_prep": prep,
    }

    col_dl1, col_dl2 = st.columns(2)
    col_dl1.download_button("📄 Download Disco Prep (.md)", data=md_export, file_name=f"{base_name}.md", mime="text/markdown", use_container_width=True)
    col_dl2.download_button("🗂️ Full bundle (.json)", data=json.dumps(full_payload, indent=2), file_name=f"{base_name}.json", mime="application/json", use_container_width=True)

    st.markdown("---")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("✏️ Re-edit dossiers and re-synthesize", use_container_width=True):
            st.session_state.phase = "research_done"
            st.rerun()
    with col_b:
        if st.button("🔄 New prep (keeps company cache)", type="primary", use_container_width=True):
            st.session_state.phase = "input"
            st.session_state.person_data = {}
            st.session_state.disco_prep = {}
            # Note: company_data and company_cache persist intentionally
            st.session_state.providers_used = {}
            st.rerun()

    with st.expander("🔍 Person dossier (post-edit)"):
        st.json(st.session_state.person_data)
    with st.expander("🏢 Company dossier (post-edit)"):
        st.json(st.session_state.company_data)

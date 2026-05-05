"""
Pion Disco Prep
===============
Pre-call discovery prep for Pion Business Development Managers.

Phased flow:
  Phase 1 — Inputs:      Company, person, title
  Phase 2 — Review:      Structured form editors for both dossiers (no JSON)
  Phase 3 — Disco Prep:  Menu of Pain + four-quadrant pitch hypothesis

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

      /* Card styling for list items in the form editor */
      .editor-card {
        background: #FFFFFF;
        border: 1px solid #E5E5DF;
        border-radius: 6px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
      }
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
    "Recommended: Perplexity for search, Anthropic for synthesis."
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
    "Pre-call prep for booked discovery meetings. Research → review → Disco Prep with Menu of Pain framework + four-quadrant pitch hypothesis."
)


# ── Form helpers for Phase 2 ──────────────────────────────────────────────────
def text_field(label: str, value, key: str, height: int = None) -> str:
    """Render a single-line or multi-line text input with the given default value."""
    val = value if isinstance(value, str) else (str(value) if value is not None else "")
    if height:
        return st.text_area(label, value=val, key=key, height=height)
    return st.text_input(label, value=val, key=key)


def list_of_strings_editor(label: str, items: list, key_prefix: str, placeholder: str = "") -> list:
    """Render a list of strings as add/remove cards. Returns the edited list."""
    if not isinstance(items, list):
        items = []

    # Track count in session state so add/remove buttons work cleanly across reruns
    count_key = f"{key_prefix}_count"
    if count_key not in st.session_state:
        st.session_state[count_key] = max(len(items), 1)

    st.markdown(f"**{label}**")
    edited = []
    for i in range(st.session_state[count_key]):
        existing = items[i] if i < len(items) else ""
        col1, col2 = st.columns([10, 1])
        with col1:
            val = st.text_input(
                f"{label} #{i+1}",
                value=existing if isinstance(existing, str) else str(existing),
                key=f"{key_prefix}_item_{i}",
                placeholder=placeholder,
                label_visibility="collapsed",
            )
        with col2:
            if st.button("✕", key=f"{key_prefix}_rm_{i}", help="Remove"):
                st.session_state[count_key] = max(0, st.session_state[count_key] - 1)
                # Shift everything down
                for j in range(i, st.session_state[count_key]):
                    nxt = st.session_state.get(f"{key_prefix}_item_{j+1}", "")
                    st.session_state[f"{key_prefix}_item_{j}"] = nxt
                st.rerun()
        if val.strip():
            edited.append(val.strip())

    if st.button(f"+ Add", key=f"{key_prefix}_add"):
        st.session_state[count_key] += 1
        st.rerun()

    return edited


def list_of_dicts_editor(label: str, items: list, schema: list, key_prefix: str) -> list:
    """
    Render a list of dict items as cards, where each card has fields per `schema`.
    schema is a list of (field_key, field_label, field_type) tuples.
    field_type: 'text' | 'textarea'
    Returns the edited list of dicts.
    """
    if not isinstance(items, list):
        items = []

    count_key = f"{key_prefix}_count"
    if count_key not in st.session_state:
        st.session_state[count_key] = max(len(items), 1)

    st.markdown(f"**{label}**")
    edited = []
    for i in range(st.session_state[count_key]):
        existing = items[i] if i < len(items) and isinstance(items[i], dict) else {}
        with st.container():
            st.markdown(f"<div class='editor-card'>", unsafe_allow_html=True)
            cols = st.columns([10, 1])
            with cols[0]:
                st.caption(f"Entry #{i+1}")
            with cols[1]:
                if st.button("✕", key=f"{key_prefix}_rm_{i}", help="Remove this entry"):
                    st.session_state[count_key] = max(0, st.session_state[count_key] - 1)
                    st.rerun()

            entry = {}
            for fkey, flabel, ftype in schema:
                widget_key = f"{key_prefix}_{i}_{fkey}"
                default = existing.get(fkey, "") if isinstance(existing, dict) else ""
                if ftype == "textarea":
                    entry[fkey] = st.text_area(flabel, value=str(default), key=widget_key, height=70)
                else:
                    entry[fkey] = st.text_input(flabel, value=str(default), key=widget_key)
            st.markdown("</div>", unsafe_allow_html=True)

            # Only keep the entry if at least one field has content
            if any(v.strip() for v in entry.values() if isinstance(v, str)):
                edited.append(entry)

    if st.button(f"+ Add another", key=f"{key_prefix}_add"):
        st.session_state[count_key] += 1
        st.rerun()

    return edited


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
                    "Verification (Beans iD core)",
                    "In-store verification",
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
                st.session_state.person_data = parse_json_object(person_raw) or {}
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
                    company_data = parse_json_object(company_raw) or {}
                    st.session_state.company_data = company_data
                    st.session_state.company_cache[company_key] = {"data": company_data, "provider": search_provider}
                    st.session_state.providers_used["company_search"] = search_provider
                except Exception as e:
                    st.error(f"Company research failed via {search_provider}: {e}")
                    st.stop()

        # Reset all editor counters so they re-init from new data
        for k in list(st.session_state.keys()):
            if k.endswith("_count"):
                del st.session_state[k]

        st.session_state.phase = "research_done"
        st.rerun()


# ── PHASE 2 — REVIEW & EDIT (structured form) ────────────────────────────────
elif st.session_state.phase == "research_done":
    st.markdown('<div class="phase-pill done">Phase 2 of 3 · Review & edit dossiers</div>', unsafe_allow_html=True)

    inputs = st.session_state.inputs
    st.markdown(f"**{inputs['company']}** · {inputs['person_name']}, *{inputs['person_title']}*")
    st.caption(
        "The research populated these fields. Edit anything that's wrong, add anything missing. "
        "Synthesis runs on whatever you save here."
    )

    person = st.session_state.person_data or {}
    company_d = st.session_state.company_data or {}

    # Two-tab layout for cleanliness
    tab_person, tab_company = st.tabs(["👤 Person dossier", "🏢 Company dossier"])

    with tab_person:
        st.caption(f"Source: {st.session_state.providers_used.get('person_search', 'unknown')}")

        person_edited = {}
        person_edited["person_name"] = text_field("Name", person.get("person_name", inputs["person_name"]), "p_name")
        person_edited["current_title"] = text_field("Current title", person.get("current_title", inputs["person_title"]), "p_title")
        person_edited["tenure_at_company"] = text_field("Tenure at company", person.get("tenure_at_company", ""), "p_tenure")
        person_edited["scope_of_role"] = text_field("Scope of role (what they own)", person.get("scope_of_role", ""), "p_scope", height=70)
        person_edited["reports_to"] = text_field("Reports to", person.get("reports_to", ""), "p_reports")
        person_edited["topics_they_gravitate_to"] = text_field("Topics they gravitate to", person.get("topics_they_gravitate_to", ""), "p_topics", height=70)
        person_edited["shared_background_hooks"] = text_field("Shared background hooks", person.get("shared_background_hooks", ""), "p_hooks", height=70)

        st.markdown("---")
        person_edited["title_driven_priorities"] = list_of_strings_editor(
            "Title-driven priorities (what they're measured on)",
            person.get("title_driven_priorities", []),
            "p_priorities",
            placeholder="e.g. Drive Gen Z brand affinity",
        )

        st.markdown("---")
        person_edited["rapport_moments"] = list_of_dicts_editor(
            "Rapport moments (recent public things to mention)",
            person.get("rapport_moments", []),
            schema=[
                ("moment", "Moment", "textarea"),
                ("source", "Source", "text"),
                ("date", "Date (YYYY-MM)", "text"),
                ("rapport_value", "Rapport value (High/Medium/Low)", "text"),
            ],
            key_prefix="p_rapport",
        )

        st.markdown("---")
        person_edited["previous_roles"] = list_of_dicts_editor(
            "Previous roles",
            person.get("previous_roles", []),
            schema=[
                ("title", "Title", "text"),
                ("company", "Company", "text"),
                ("duration", "Duration", "text"),
                ("relevance", "Why it matters for this call", "textarea"),
            ],
            key_prefix="p_prev_roles",
        )

        st.markdown("---")
        person_edited["public_footprint"] = list_of_dicts_editor(
            "Public footprint (podcasts, panels, press, posts)",
            person.get("public_footprint", []),
            schema=[
                ("type", "Type (podcast/panel/article/post)", "text"),
                ("topic", "Topic", "textarea"),
                ("source", "Source", "text"),
                ("date", "Date (YYYY-MM)", "text"),
            ],
            key_prefix="p_footprint",
        )

        st.markdown("---")
        person_edited["research_confidence"] = text_field("Research confidence (High/Medium/Low)", person.get("research_confidence", ""), "p_conf")
        person_edited["research_gaps"] = text_field("Research gaps", person.get("research_gaps", ""), "p_gaps", height=70)

    with tab_company:
        st.caption(f"Source: {st.session_state.providers_used.get('company_search', 'unknown')}")

        company_edited = {}
        company_edited["company"] = text_field("Company", company_d.get("company", inputs["company"]), "c_name")

        col1, col2 = st.columns(2)
        with col1:
            company_edited["segment"] = text_field("Segment", company_d.get("segment", ""), "c_segment")
            company_edited["us_location_count"] = text_field("US location count", company_d.get("us_location_count", ""), "c_locs")
            company_edited["us_presence"] = text_field("US presence (Yes/Limited/No)", company_d.get("us_presence", ""), "c_us")
            company_edited["ecommerce_presence"] = text_field("Ecommerce presence", company_d.get("ecommerce_presence", ""), "c_ecom")
            company_edited["physical_store_presence"] = text_field("Physical store presence", company_d.get("physical_store_presence", ""), "c_phys")
        with col2:
            company_edited["has_student_discount"] = text_field("Has student discount?", company_d.get("has_student_discount", ""), "c_sd")
            company_edited["student_discount_provider"] = text_field("Student discount provider", company_d.get("student_discount_provider", ""), "c_sdp")
            company_edited["has_loyalty_app"] = text_field("Has loyalty app?", company_d.get("has_loyalty_app", ""), "c_la")
            company_edited["loyalty_app_name"] = text_field("Loyalty app name", company_d.get("loyalty_app_name", ""), "c_lan")
            company_edited["loyalty_strategic_priority"] = text_field("Loyalty is strategic priority?", company_d.get("loyalty_strategic_priority", ""), "c_lsp")

        company_edited["loyalty_tech_stack"] = text_field("Loyalty tech stack", company_d.get("loyalty_tech_stack", ""), "c_lts")
        company_edited["student_discount_details"] = text_field("Student discount details", company_d.get("student_discount_details", ""), "c_sdd", height=70)
        company_edited["runs_general_promos"] = text_field("Runs general promos?", company_d.get("runs_general_promos", ""), "c_promos")
        company_edited["seasonal_focus"] = text_field("Seasonal focus", company_d.get("seasonal_focus", ""), "c_season", height=70)
        company_edited["leadership_changes_last_12mo"] = text_field("Leadership changes (last 12mo)", company_d.get("leadership_changes_last_12mo", ""), "c_leadership", height=70)

        st.markdown("---")
        company_edited["promo_examples"] = list_of_strings_editor(
            "Promo examples",
            company_d.get("promo_examples", []),
            "c_promo_ex",
            placeholder="e.g. BOGO Tuesdays via app",
        )

        st.markdown("---")
        company_edited["recent_news"] = list_of_dicts_editor(
            "Recent news",
            company_d.get("recent_news", []),
            schema=[
                ("headline", "Headline", "textarea"),
                ("date", "Date (YYYY-MM)", "text"),
                ("relevance_to_pion", "Relevance to Pion", "textarea"),
            ],
            key_prefix="c_news",
        )

        st.markdown("---")
        col3, col4 = st.columns(2)
        with col3:
            company_edited["pion_product_fit"] = text_field("Pion product fit", company_d.get("pion_product_fit", ""), "c_fit")
            company_edited["displacement_target"] = text_field("Displacement target", company_d.get("displacement_target", ""), "c_disp")
        with col4:
            company_edited["research_confidence"] = text_field("Research confidence", company_d.get("research_confidence", ""), "c_conf")
        company_edited["fit_rationale"] = text_field("Fit rationale", company_d.get("fit_rationale", ""), "c_rat", height=70)
        company_edited["research_gaps"] = text_field("Research gaps", company_d.get("research_gaps", ""), "c_gaps", height=70)

    # Action buttons
    st.markdown("---")
    col_a, _, col_c = st.columns([1, 1, 1])
    with col_a:
        if st.button("⬅ Back to inputs", use_container_width=True):
            st.session_state.phase = "input"
            st.rerun()
    with col_c:
        build = st.button("🎯 Build Disco Prep", type="primary", use_container_width=True)

    if build:
        # Persist edits
        st.session_state.person_data = {k: v for k, v in person_edited.items() if v not in ([], "", None)}
        st.session_state.company_data = {k: v for k, v in company_edited.items() if v not in ([], "", None)}

        with st.spinner(f"Synthesising Disco Prep via {synth_provider}…"):
            synth_user = build_synthesis_user_prompt(
                company=inputs["company"],
                person_name=inputs["person_name"],
                person_title=inputs["person_title"],
                product_angle=inputs["product_angle"],
                extra_context=inputs["extra_context"],
                person_data=st.session_state.person_data,
                company_data=st.session_state.company_data,
            )
            try:
                prep_raw = call_synthesis(
                    system_prompt=SYNTHESIS_SYSTEM_PROMPT,
                    user_prompt=synth_user,
                    api_keys=api_keys,
                    provider=synth_provider,
                )
                disco_prep = parse_json_object(prep_raw) or {}
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
            st.session_state.providers_used = {}
            # Clear all editor counts so the form re-initializes
            for k in list(st.session_state.keys()):
                if k.endswith("_count"):
                    del st.session_state[k]
            st.rerun()

    with st.expander("🔍 Person dossier (post-edit)"):
        st.json(st.session_state.person_data)
    with st.expander("🏢 Company dossier (post-edit)"):
        st.json(st.session_state.company_data)

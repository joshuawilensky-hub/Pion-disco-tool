# Pion Disco Prep

Pre-call discovery prep for Pion Business Development Managers.

## What it does

You've got a discovery call booked. You enter:
- The **company** (e.g. Chipotle Mexican Grill)
- The **person** on the call (full name)
- Their **exact title** (from the calendar invite)
- Optional: which Pion product angle to lead with

The tool runs a three-phase flow:

1. **Phase 1 — Inputs:** company, person, title
2. **Phase 2 — Review:** structured form editors for both research dossiers (no JSON). Edit anything wrong, add anything missing.
3. **Phase 3 — Disco Prep:** one-page brief with the Menu of Pain framework + four-quadrant pitch hypothesis

The output is built around the **Menu of Pain** discovery technique:
- 3 pain options tuned to the company's segment + person's title
- Each option has a SPIN-style pain funnel (Problem → Implication → Need-Payoff)
- "If they pick this, pivot to [Pion product]" guidance
- Listen-for signals tied to mid-call product pivots
- CHAMP qualifiers for the back third of the call
- Four-quadrant hypothesis (Strategic Objectives / Current Challenge / How We Solve / Expected Outcome) using real Pion proof points
- Rapport opener tied to a verified recent moment, landmines, ideal next step

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

Add API keys via `st.secrets` (Streamlit Cloud → Settings → Secrets):

```toml
PERPLEXITY_API_KEY = "pplx-..."
ANTHROPIC_API_KEY  = "sk-ant-..."
OPENAI_API_KEY     = "sk-..."
GEMINI_API_KEY     = "..."
```

You don't need all four — the dropdowns only show providers with valid keys.

## Provider matrix — what works for what

This tool has two distinct steps, and different providers are good at different jobs:

| Step | Best | Backup | Skip |
|---|---|---|---|
| **Search** (live web research on person + company) | **Perplexity Sonar** | Anthropic web_search | OpenAI, Gemini |
| **Synthesis** (Disco Prep generation) | **Anthropic Claude** | OpenAI gpt-4o | Perplexity, Gemini |

**Why Perplexity for search:** Sonar models are purpose-built for "research a topic, return cited findings in structured form." That's exactly the search step. ~$0.005/query, $5 minimum to top up.

**Why Anthropic for synthesis:** Claude reasons better over messy multi-source dossiers and is more consistent at returning the structured JSON the tool expects.

**Why skip OpenAI for search:** `gpt-4o-search-preview` returns surface-level findings — fits the schema but lacks the specifics that make the Disco Prep useful. It's fine as a synthesis backup.

**Why skip Gemini:** Free tier is restricted (often `limit: 0` regardless of usage), making it unreliable. Paid tier offers no advantage over Anthropic.

**Recommended config:** Perplexity for search, Anthropic for synthesis. ~$0.05–0.08 per Disco Prep.

## File structure

```
pion-discovery/
├── app.py            # Streamlit UI, phased flow, form editors
├── prompts.py        # Person research, company research, Menu of Pain synthesis
├── providers.py      # Provider routing across Perplexity / Anthropic / OpenAI / Gemini
├── utils.py          # JSON parsing + Disco Prep markdown rendering
└── requirements.txt
```

## Path to integration with the existing SDR agent

Standalone for v1. To integrate later:

1. **Reuse the company research** — the SDR enricher already pulls company signal. Synthesis here can take that JSON directly instead of re-fetching.
2. **Add a "Discovery Prep" tab** to the SDR agent that takes a row from the enriched leads table + a person name/title, runs only the person-research and synthesis steps, and renders the Disco Prep.
3. **Persist past prep sheets** — once integrated, store them keyed on (company, person) so you can review and learn from how calls actually went vs. what the tool predicted.

## What v2 could add

- Save call outcomes against each Disco Prep → fine-tune hypotheses over time
- Multi-attendee mode (often 2–3 stakeholders on one call)
- Calendar integration to auto-prepare prep sheets the day before each booked discovery
- Post-call recap mode that captures CHAMP answers and drafts the follow-up email

# Pion-disco-tool

Pre-call discovery prep for Pion Business Development Managers.

## What it does

You've got a call booked. You enter:
- The **company** (e.g. Chipotle Mexican Grill)
- The **person** on the call (full name)
- Their **exact title** (from the calendar invite)
- Optional: which Pion product angle to lead with

The tool runs a three-step pipeline:

1. **Live person research** — pulls public footprint on the named contact (LinkedIn, podcasts, panels, press quotes, prior roles, what they publicly think about)
2. **Live company research** — Pion-specific signal (UNiDAYS/SheerID presence, loyalty app status, promo cadence, recent news)
3. **Synthesis** — turns both dossiers into a one-page cheat sheet you scan in 90 seconds before the call

The cheat sheet contains:
- **Person dossier** — who they are, what changes about this call given who they are
- **Company snapshot** — Pion product to lead with, displacement target if any
- **Hypotheses** — what to walk in believing
- **Discovery questions** — Situation → Pain → Impact → Vision, tuned to the person
- **Listen-for signals** — phrases that unlock specific Pion product pivots mid-call
- **Landmines** — specific to this person/company
- **Proof points to load** — case studies/stats to have ready
- **Opening line** — built off something concrete from the research
- **Ideal next step** — what success on this call looks like

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

Add API keys in the sidebar. You don't need all four — the waterfall gracefully falls through any provider you haven't configured.

## Provider waterfall

**Recommended config:**
- Search step → **Perplexity** (Sonar — purpose-built for live cited search, cheapest)
- Synthesis step → **Anthropic** (Claude Sonnet — best reasoning over messy multi-source inputs)

The waterfall order is: your selected primary → Perplexity → Anthropic → OpenAI → Gemini (deduped). If your primary fails, the next provider with a configured key is tried.

## File structure

```
pion-discovery/
├── app.py            # Streamlit UI + pipeline orchestration
├── prompts.py        # Person research, company research, synthesis prompts
├── providers.py      # Waterfall across Perplexity / Anthropic / OpenAI / Gemini
├── utils.py          # JSON parsing + cheat sheet markdown rendering
└── requirements.txt
```

## Path to integration with the existing SDR agent

This is intentionally built as a standalone app for v1. To integrate later:

1. **Reuse the company research** — your existing enricher already pulls company signal. The synthesis step here can take that JSON directly instead of re-fetching.
2. **Add a "Discovery Prep" tab** to the SDR agent app that takes a row from the enriched leads table + a person name/title, runs only the person-research and synthesis steps, and renders the cheat sheet.
3. **Persist past cheat sheets** — once integrated, store them keyed on (company, person) so you can review and learn from how calls actually went vs. what the tool predicted.

## What v2 would add

- Save call outcomes against each cheat sheet → fine-tune hypotheses over time
- Multi-attendee mode (you're often on calls with 2–3 stakeholders)
- Rep-specific tuning (your style, your strongest proof points)
- Calendar integration so the tool prepares cheat sheets automatically the day before each booked discovery

"""
Provider waterfall for the Pion Discovery tool.

Two entry points:
  - call_with_search: web-search-enabled call (for person & company research)
  - call_for_synthesis: pure-LLM call (for cheat sheet synthesis)

Both implement the waterfall: try primary, fall through to others on failure.
Order tried = [primary] + [the rest in canonical order, deduped]
Canonical order: perplexity, anthropic, openai, gemini

Each provider returns (text, provider_name_used) or (None, None) if all fail.
"""

import streamlit as st
from typing import Optional, Tuple, Dict


CANONICAL_ORDER = ["perplexity", "anthropic", "openai", "gemini"]


def _build_order(primary: str) -> list:
    rest = [p for p in CANONICAL_ORDER if p != primary]
    return [primary] + rest


# ─────────────────────────────────────────────────────────────────────────────
# Search-enabled calls (live web)
# ─────────────────────────────────────────────────────────────────────────────
def call_with_search(prompt: str, api_keys: Dict[str, str], primary: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Try providers in waterfall order until one returns text.
    Each provider uses its own native web-search capability.
    """
    order = _build_order(primary)
    last_error = None

    for provider in order:
        key = api_keys.get(provider, "").strip()
        if not key:
            continue
        try:
            if provider == "perplexity":
                text = _perplexity_search(prompt, key)
            elif provider == "anthropic":
                text = _anthropic_search(prompt, key)
            elif provider == "openai":
                text = _openai_search(prompt, key)
            elif provider == "gemini":
                text = _gemini_search(prompt, key)
            else:
                continue

            if text and text.strip():
                return text, provider
        except Exception as e:
            last_error = f"{provider}: {e}"
            st.warning(f"⚠️ {provider} failed ({e}), trying next provider…")
            continue

    if last_error:
        st.error(f"All search providers failed. Last error: {last_error}")
    return None, None


# ─────────────────────────────────────────────────────────────────────────────
# Synthesis calls (no search needed — reasoning over given inputs)
# ─────────────────────────────────────────────────────────────────────────────
def call_for_synthesis(
    system_prompt: str,
    user_prompt: str,
    api_keys: Dict[str, str],
    primary: str,
) -> Tuple[Optional[str], Optional[str]]:
    """Synthesis step — pure reasoning over the dossiers."""
    order = _build_order(primary)
    last_error = None

    for provider in order:
        key = api_keys.get(provider, "").strip()
        if not key:
            continue
        try:
            if provider == "perplexity":
                text = _perplexity_chat(system_prompt, user_prompt, key)
            elif provider == "anthropic":
                text = _anthropic_chat(system_prompt, user_prompt, key)
            elif provider == "openai":
                text = _openai_chat(system_prompt, user_prompt, key)
            elif provider == "gemini":
                text = _gemini_chat(system_prompt, user_prompt, key)
            else:
                continue

            if text and text.strip():
                return text, provider
        except Exception as e:
            last_error = f"{provider}: {e}"
            st.warning(f"⚠️ {provider} synthesis failed ({e}), trying next provider…")
            continue

    if last_error:
        st.error(f"All synthesis providers failed. Last error: {last_error}")
    return None, None


# ─────────────────────────────────────────────────────────────────────────────
# Per-provider implementations — search variants
# ─────────────────────────────────────────────────────────────────────────────
def _perplexity_search(prompt: str, api_key: str) -> str:
    """Perplexity Sonar is search-native — every call is a live web search."""
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url="https://api.perplexity.ai")
    response = client.chat.completions.create(
        model="sonar",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2500,
    )
    return response.choices[0].message.content or ""


def _anthropic_search(prompt: str, api_key: str) -> str:
    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in message.content if hasattr(block, "text"))


def _openai_search(prompt: str, api_key: str) -> str:
    """OpenAI's gpt-4o-search-preview supports web search."""
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-search-preview",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2500,
    )
    return response.choices[0].message.content or ""


def _gemini_search(prompt: str, api_key: str) -> str:
    """Gemini 2.0 Flash with the google_search tool."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )
    return response.text or ""


# ─────────────────────────────────────────────────────────────────────────────
# Per-provider implementations — chat (synthesis) variants
# ─────────────────────────────────────────────────────────────────────────────
def _perplexity_chat(system_prompt: str, user_prompt: str, api_key: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url="https://api.perplexity.ai")
    response = client.chat.completions.create(
        model="sonar",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=3500,
    )
    return response.choices[0].message.content or ""


def _anthropic_chat(system_prompt: str, user_prompt: str, api_key: str) -> str:
    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return "".join(block.text for block in message.content if hasattr(block, "text"))


def _openai_chat(system_prompt: str, user_prompt: str, api_key: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=3500,
    )
    return response.choices[0].message.content or ""


def _gemini_chat(system_prompt: str, user_prompt: str, api_key: str) -> str:
    """Gemini doesn't have a separate system role — prepend system to the user content."""
    from google import genai

    client = genai.Client(api_key=api_key)
    combined = f"{system_prompt}\n\n---\n\n{user_prompt}"
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=combined,
    )
    return response.text or ""

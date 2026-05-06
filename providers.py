"""
Provider routing for Pion Disco Prep.

Picker model: caller specifies exactly one provider per step.
No automatic fallback — if a provider fails, the exception bubbles up
and the UI shows it. This matches the Notion Mid-Market Prospector pattern
and keeps cost/quality predictable.

Two entry points:
  - call_search:    web-search-enabled call (person + company research)
  - call_synthesis: pure-LLM call (turning dossiers into a Disco Prep)

Plus:
  - available_providers: returns the list of providers with a non-empty key
"""

from typing import Dict, List


CANONICAL_ORDER = ["perplexity", "anthropic", "openai", "gemini"]


def available_providers(api_keys: Dict[str, str]) -> List[str]:
    """Return providers that have a non-empty key, in canonical display order."""
    return [p for p in CANONICAL_ORDER if (api_keys.get(p) or "").strip()]


# ─────────────────────────────────────────────────────────────────────────────
# Public entry points
# ─────────────────────────────────────────────────────────────────────────────
def call_search(prompt: str, api_keys: Dict[str, str], provider: str) -> str:
    """Run a live-web-search call with the chosen provider."""
    key = (api_keys.get(provider) or "").strip()
    if not key:
        raise ValueError(f"No API key configured for {provider}")

    if provider == "perplexity":
        return _perplexity_search(prompt, key)
    if provider == "anthropic":
        return _anthropic_search(prompt, key)
    if provider == "openai":
        return _openai_search(prompt, key)
    if provider == "gemini":
        return _gemini_search(prompt, key)
    raise ValueError(f"Unknown provider: {provider}")


def call_synthesis(system_prompt: str, user_prompt: str, api_keys: Dict[str, str], provider: str) -> str:
    """Run a synthesis (no web search) call with the chosen provider."""
    key = (api_keys.get(provider) or "").strip()
    if not key:
        raise ValueError(f"No API key configured for {provider}")

    if provider == "perplexity":
        return _perplexity_chat(system_prompt, user_prompt, key)
    if provider == "anthropic":
        return _anthropic_chat(system_prompt, user_prompt, key)
    if provider == "openai":
        return _openai_chat(system_prompt, user_prompt, key)
    if provider == "gemini":
        return _gemini_chat(system_prompt, user_prompt, key)
    raise ValueError(f"Unknown provider: {provider}")


# ─────────────────────────────────────────────────────────────────────────────
# Search-enabled implementations
# ─────────────────────────────────────────────────────────────────────────────
def _perplexity_search(prompt: str, api_key: str) -> str:
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
        model="claude-3-5-sonnet-latest",
        max_tokens=3000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in message.content if hasattr(block, "text"))


def _openai_search(prompt: str, api_key: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-search-preview",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2500,
    )
    return response.choices[0].message.content or ""


def _gemini_search(prompt: str, api_key: str) -> str:
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
# Chat (synthesis) implementations
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
        model="claude-3-5-sonnet-latest",
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
    from google import genai
    client = genai.Client(api_key=api_key)
    combined = f"{system_prompt}\n\n---\n\n{user_prompt}"
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=combined,
    )
    return response.text or ""

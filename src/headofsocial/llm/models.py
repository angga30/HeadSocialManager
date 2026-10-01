"""Resolve per-role LLM models via ADK's LiteLlm (multi-provider)."""

import os
from functools import cache

from google.adk.models.lite_llm import LiteLlm

from headofsocial.config import settings

# We intentionally route Gemini through LiteLLM for multi-provider consistency with the
# other roles (OpenAI/Anthropic/Ollama). Silence ADK's nudge to use its native Gemini.
os.environ.setdefault("ADK_SUPPRESS_GEMINI_LITELLM_WARNINGS", "true")

_ROLES = frozenset(
    {"positioning", "planning", "content", "media", "publishing", "orchestrator", "default"}
)


@cache
def role_model_string(role: str) -> str:
    """Return the LiteLLM model string configured for a role."""
    if role not in _ROLES:
        role = "default"
    return settings.role_models[role]


def get_model(role: str) -> LiteLlm:
    """Return an ADK model object for a role. Swap providers via .env — not code."""
    return LiteLlm(model=role_model_string(role))
"""Normalize LangChain LLM usage metadata into a stable token_usage dict."""

from __future__ import annotations

from typing import Any


def empty_token_usage() -> dict[str, int]:
    """Zeroed token counters for paths that do not call an LLM."""
    return {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }


def summarize_usage_metadata(usage_metadata: dict[str, Any] | None) -> dict[str, int]:
    """Sum prompt / completion / total tokens across models in a callback map.

    ``UsageMetadataCallbackHandler.usage_metadata`` looks like::

        {"gpt-4o-mini": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}}

    Returns a flat dict suitable for API responses and DB JSONB storage.
    """
    if not usage_metadata:
        return empty_token_usage()

    prompt = 0
    completion = 0
    total = 0
    for model_usage in usage_metadata.values():
        if not isinstance(model_usage, dict):
            continue
        inp = int(model_usage.get("input_tokens") or model_usage.get("prompt_tokens") or 0)
        out = int(model_usage.get("output_tokens") or model_usage.get("completion_tokens") or 0)
        tot = int(model_usage.get("total_tokens") or (inp + out))
        prompt += inp
        completion += out
        total += tot

    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": total,
    }

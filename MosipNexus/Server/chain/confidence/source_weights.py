"""Static confidence config — source-type base weights and signal blend weights.

Base weights reflect how much a source type should be trusted *before* any
retrieval/feedback history exists. ``verified_solutions``, ``environment_logs``,
``dsl_run_reports``, and ``kt_video_transcripts`` are reserved for the
environment-diagnostic system (log/DSL ingestion) — not populated today, but
scoring already accounts for them so no schema/config change is needed when
that system ships.

Every weight is env-overridable, following the ``config.settings`` pattern.
"""

from __future__ import annotations

import os

SOURCE_BASE_WEIGHTS: dict[str, float] = {
    # Human-verified fixes — highest trust once the feedback loop writes these.
    "verified_solutions": float(os.getenv("CONFIDENCE_WEIGHT_VERIFIED_SOLUTIONS", "0.95")),
    # Live today.
    "docs": float(os.getenv("CONFIDENCE_WEIGHT_DOCS", "0.80")),
    "esignet": float(os.getenv("CONFIDENCE_WEIGHT_ESIGNET", "0.80")),
    "confluence": float(os.getenv("CONFIDENCE_WEIGHT_CONFLUENCE", "0.75")),
    "github": float(os.getenv("CONFIDENCE_WEIGHT_GITHUB", "0.70")),
    "code": float(os.getenv("CONFIDENCE_WEIGHT_CODE", "0.70")),
    # Reserved — diagnostic system, not ingested yet.
    "kt_video_transcripts": float(os.getenv("CONFIDENCE_WEIGHT_KT_VIDEO", "0.65")),
    # Live today.
    "jira": float(os.getenv("CONFIDENCE_WEIGHT_JIRA", "0.60")),
    "community": float(os.getenv("CONFIDENCE_WEIGHT_COMMUNITY", "0.60")),
    "website": float(os.getenv("CONFIDENCE_WEIGHT_WEBSITE", "0.60")),
    # Reserved — diagnostic system, not ingested yet.
    "environment_logs": float(os.getenv("CONFIDENCE_WEIGHT_ENV_LOGS", "0.50")),
    "dsl_run_reports": float(os.getenv("CONFIDENCE_WEIGHT_DSL_REPORTS", "0.50")),
}
DEFAULT_BASE_WEIGHT = float(os.getenv("CONFIDENCE_WEIGHT_DEFAULT", "0.55"))


def base_weight(source_type: str) -> float:
    """Base trust weight for a source type, falling back to the default."""
    return SOURCE_BASE_WEIGHTS.get(source_type or "", DEFAULT_BASE_WEIGHT)


# ── Per-chunk signal blend (must sum to ~1.0) ───────────────────────────────────
# W_RESOLUTION stays 0.0 until the log-resolution watcher (diagnostic system)
# exists — the accumulator column is already there, so activating it later is a
# one-line change here, not a schema migration.
W_BASE       = float(os.getenv("CONFIDENCE_W_BASE", "0.40"))
W_RETRIEVAL  = float(os.getenv("CONFIDENCE_W_RETRIEVAL", "0.20"))
W_AGREEMENT  = float(os.getenv("CONFIDENCE_W_AGREEMENT", "0.15"))
W_RECENCY    = float(os.getenv("CONFIDENCE_W_RECENCY", "0.10"))
W_FOLLOWUP   = float(os.getenv("CONFIDENCE_W_FOLLOWUP", "0.05"))
W_EXPLICIT   = float(os.getenv("CONFIDENCE_W_EXPLICIT", "0.10"))
W_RESOLUTION = float(os.getenv("CONFIDENCE_W_RESOLUTION", "0.00"))

# Retrieval-count normalisation — chunk retrieved this many times reaches full signal weight.
RETRIEVAL_SATURATION_COUNT = int(os.getenv("CONFIDENCE_RETRIEVAL_SATURATION", "100"))

# Weekly recency decay multiplier (compounded per week since first_seen_at).
RECENCY_DECAY_PER_WEEK = float(os.getenv("CONFIDENCE_RECENCY_DECAY", "0.95"))
# verified_solutions don't decay — a confirmed fix doesn't go stale just because it's old.
RECENCY_EXEMPT_SOURCE_TYPES = {"verified_solutions"}

# ── Answer-level blend: this-query relevance vs. chunk's historical reliability ──
# Keeps today's behaviour (relevance-driven) dominant while blending in history,
# rather than replacing the existing MMR-relevance signal outright.
ANSWER_RELEVANCE_WEIGHT = float(os.getenv("CONFIDENCE_ANSWER_RELEVANCE_WEIGHT", "0.6"))
ANSWER_HISTORY_WEIGHT   = float(os.getenv("CONFIDENCE_ANSWER_HISTORY_WEIGHT", "0.4"))

# Explicit feedback nudge size (accumulator moves toward 1.0 / 0.0 by this much per click).
EXPLICIT_FEEDBACK_STEP = float(os.getenv("CONFIDENCE_EXPLICIT_STEP", "0.15"))
# Follow-up-looks-incomplete nudge (only the negative half is implemented — see scorer.py).
FOLLOWUP_NEGATIVE_STEP = float(os.getenv("CONFIDENCE_FOLLOWUP_STEP", "0.05"))
# Multi-source agreement nudge per additional independently-retrieved source type.
AGREEMENT_STEP = float(os.getenv("CONFIDENCE_AGREEMENT_STEP", "0.05"))

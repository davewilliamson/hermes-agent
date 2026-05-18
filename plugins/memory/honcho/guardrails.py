"""Write-side guardrails for durable Honcho memory.

Honcho conclusions and peer cards are shared, long-lived representation data.
Keep transient task state, credentials, raw logs, and implementation artifacts out
of this layer so future sessions and other agents do not inherit stale work.
"""

from __future__ import annotations

import re
from typing import Any

MAX_DURABLE_FACT_CHARS = 1200

BLOCKED_DURABLE_FACT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"github\.com/login/device", re.I), "device-auth flow URL"),
    (re.compile(r"\b[A-Z0-9]{4}-[A-Z0-9]{4}\b"), "device/auth code"),
    (re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b"), "GitHub token material"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b", re.I), "GitHub token material"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "API key material"),
    (re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{20,}\b", re.I), "Slack token material"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key material"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\b"), "JWT/bearer token material"),
    (re.compile(r"\b(?:ssh-rsa|ssh-ed25519|ecdsa-sha2-[A-Za-z0-9-]+)\s+\S+", re.I), "raw SSH public key"),
    (re.compile(r"BEGIN [A-Z ]*PRIVATE KEY", re.I), "private key material"),
    (re.compile(r"\b(currently working|working on|in progress|awaiting|waiting for|blocked on|next task is|next step is|todo)\b", re.I), "transient task state"),
    (re.compile(r"\b(?:PR|pull request|issue)\s*#?\d+\b", re.I), "stale PR/issue artifact"),
    (re.compile(r"\b(?:commit\s+)?[0-9a-f]{12,40}\b", re.I), "stale commit artifact"),
    (re.compile(r"\bworkflow run\b", re.I), "stale workflow-run artifact"),
    (re.compile(r"\b(?:Traceback \(most recent call last\)|Exception in thread|ERROR\s+\[[^\]]+\])", re.I), "raw log/stack trace"),
]


def honcho_durable_fact_guardrail(fact: str) -> str | None:
    """Return a block reason when a fact is unsafe for durable Honcho memory."""
    text = (fact or "").strip()
    if not text:
        return "empty conclusion"
    if len(text) > MAX_DURABLE_FACT_CHARS:
        return "too long for durable memory; summarize before saving"
    for pattern, reason in BLOCKED_DURABLE_FACT_PATTERNS:
        if pattern.search(text):
            return reason
    return None


def honcho_peer_card_guardrail(card: Any) -> str | None:
    """Return a block reason when a peer-card update contains unsafe durable facts."""
    if not isinstance(card, list):
        return "peer card must be a list of durable facts"
    for index, fact in enumerate(card, start=1):
        blocked_reason = honcho_durable_fact_guardrail(str(fact) if fact is not None else "")
        if blocked_reason:
            return f"peer-card fact {index}: {blocked_reason}"
    return None

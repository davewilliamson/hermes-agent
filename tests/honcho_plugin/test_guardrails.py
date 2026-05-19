"""Tests for Honcho durable-memory write guardrails."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from plugins.memory.honcho.guardrails import (
    honcho_durable_fact_guardrail,
    honcho_peer_card_guardrail,
)
from plugins.memory.honcho.session import HonchoSession, HonchoSessionManager


@pytest.mark.parametrize(
    "fact",
    [
        "Dave prefers concise terminal-friendly summaries.",
        "Dave's Hermes fleet uses Mission Control for lifecycle status.",
        "For Dave's BMS2 project, Obsidian is the durable planning source.",
    ],
)
def test_durable_fact_guardrail_allows_stable_preferences_and_fleet_facts(fact):
    assert honcho_durable_fact_guardrail(fact) is None


@pytest.mark.parametrize(
    ("fact", "reason"),
    [
        ("Currently working on PR #123 and waiting for CI.", "transient task state"),
        ("Next step is to rerun workflow run 98765.", "transient task state"),
        ("Go to https://github.com/login/device and enter ABCD-EFGH.", "device-auth flow URL"),
        ("Temporary token " + "ghp_" + "abcdefghijklmnopqrstuvwxyz", "GitHub token material"),
        ("OpenAI token " + "sk-" + "abcdefghijklmnopqrstuvwxyz", "API key material"),
        (
            "JWT " + "eyJ" + "abcdefghijklmnopqrstuvwxyz" + "." + "ABCDEFGHIJKLMNOPQRSTUVWXYZ" + "." + "abcdefghijklmno",
            "JWT/bearer token material",
        ),
        ("-----" + "BEGIN " + "PRIVATE KEY" + "-----\nredacted\n-----END PRIVATE KEY-----", "private key material"),
        ("PR #42 fixes the issue.", "stale PR/issue artifact"),
        ("issue 314 is blocked.", "stale PR/issue artifact"),
        ("commit deadbeefcafebabe changed config.", "stale commit artifact"),
        ("workflow run failed.", "stale workflow-run artifact"),
        ("Traceback (most recent call last):\n  File \"x\", line 1", "raw log/stack trace"),
        ("A" * 1201, "too long for durable memory"),
    ],
)
def test_durable_fact_guardrail_blocks_transient_secret_artifact_and_raw_cases(fact, reason):
    assert reason in honcho_durable_fact_guardrail(fact)


def test_peer_card_guardrail_allows_all_durable_facts():
    card = [
        "Dave prefers concise replies.",
        "Dave's agents use Mission Control for lifecycle status.",
    ]
    assert honcho_peer_card_guardrail(card) is None


def test_peer_card_guardrail_blocks_one_unsafe_fact():
    card = ["Dave prefers concise replies.", "Currently working on issue #55."]
    assert honcho_peer_card_guardrail(card) == "peer-card fact 2: transient task state"


def _manager_with_session():
    mgr = HonchoSessionManager.__new__(HonchoSessionManager)
    mgr._cache = {}
    mgr._ai_observe_others = True
    session = HonchoSession(
        key="test",
        user_peer_id="user-peer",
        assistant_peer_id="ai-peer",
        honcho_session_id="sid",
    )
    mgr._cache["test"] = session
    return mgr, session


def test_manager_create_conclusion_sink_allows_durable_fact():
    mgr, _session = _manager_with_session()
    observer = MagicMock()
    conclusions_scope = MagicMock()
    observer.conclusions_of.return_value = conclusions_scope
    mgr._get_or_create_peer = MagicMock(return_value=observer)
    mgr._resolve_peer_id = MagicMock(return_value="user-peer")

    result = mgr.create_conclusion("test", "Dave prefers concise local-time updates.")

    assert result is True
    conclusions_scope.create.assert_called_once_with(
        [{"content": "Dave prefers concise local-time updates.", "session_id": "sid"}]
    )


def test_manager_create_conclusion_sink_blocks_unsafe_fact_before_honcho_call():
    mgr, _session = _manager_with_session()
    mgr._get_or_create_peer = MagicMock()
    mgr._resolve_peer_id = MagicMock(return_value="user-peer")

    result = mgr.create_conclusion("test", "Currently working on PR #123.")

    assert result is False
    mgr._resolve_peer_id.assert_not_called()
    mgr._get_or_create_peer.assert_not_called()


def test_manager_set_peer_card_sink_allows_durable_card():
    mgr, _session = _manager_with_session()
    peer_obj = MagicMock()
    peer_obj.set_card.return_value = ["Dave prefers concise replies."]
    mgr._get_or_create_peer = MagicMock(return_value=peer_obj)
    mgr._resolve_peer_id = MagicMock(return_value="user-peer")

    result = mgr.set_peer_card("test", ["Dave prefers concise replies."])

    assert result == ["Dave prefers concise replies."]
    peer_obj.set_card.assert_called_once_with(["Dave prefers concise replies."])


def test_manager_set_peer_card_sink_blocks_unsafe_card_before_honcho_call():
    mgr, _session = _manager_with_session()
    mgr._get_or_create_peer = MagicMock()
    mgr._resolve_peer_id = MagicMock(return_value="user-peer")

    result = mgr.set_peer_card("test", ["GitHub token is " + "ghp_" + "abcdefghijklmnopqrstuvwxyz"])

    assert result is None
    mgr._resolve_peer_id.assert_not_called()
    mgr._get_or_create_peer.assert_not_called()

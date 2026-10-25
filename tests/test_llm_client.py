"""Tests for LLM output hygiene: reasoning-model <think> leak stripping."""
import os
from types import SimpleNamespace

from app.adapters.llm_client import LLMClient, strip_think_tags


def test_strip_full_think_block():
    assert strip_think_tags("<think>secret reasoning</think>Final answer.") == "Final answer."


def test_strip_multiline_think_block():
    raw = "<think>\nline1\nline2\n</think>\n\nVerdict: ACCEPT"
    assert strip_think_tags(raw) == "Verdict: ACCEPT"


def test_strip_lone_closing_tag_keeps_tail():
    raw = "Let me reason about stock levels step by step...</think>The answer is PEER_TRANSFER."
    assert strip_think_tags(raw) == "The answer is PEER_TRANSFER."


def test_strip_lone_closing_tag_with_empty_tail_keeps_text_without_tag():
    out = strip_think_tags("only reasoning here</think>")
    assert "</think>" not in out
    assert "only reasoning here" in out


def test_strip_stray_opening_tag_and_plain_text_untouched():
    assert "<think>" not in strip_think_tags("<think>dangling")
    assert strip_think_tags("plain text with no tags") == "plain text with no tags"
    assert strip_think_tags("") == ""


def test_generate_strips_think_from_live_response(monkeypatch):
    """Simulate a live (non-sample) provider that leaks </think>; output text must be clean."""
    monkeypatch.setenv("SAMPLE_MODE", "false")
    client = LLMClient()
    client.sample_mode = False

    def fake_create(**kwargs):
        msg = SimpleNamespace(content="chain of thought...</think>Clean answer", reasoning_content=None)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=msg)],
            model="fake/model",
            usage=None,
        )

    client.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
    )
    res = client.generate("hello")
    assert res["text"] == "Clean answer"
    assert "think" not in res["text"].lower()
    assert res["fallback"] is False and res["llm_used"] is True

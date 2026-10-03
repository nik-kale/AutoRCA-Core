"""
Tests for the Anthropic LLM wrapper, using a stand-in client (no network).
"""

import sys
import types
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from autorca_core.model.graph import Dependency, IncidentNode, IncidentType, ServiceGraph
from autorca_core.reasoning import llm as llm_module
from autorca_core.reasoning.llm import AnthropicLLM, DummyLLM
from autorca_core.reasoning.rules import RootCauseCandidate


class FakeAPIError(Exception):
    def __init__(self, status_code):
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code


def _response(*blocks, stop_reason="end_turn"):
    return SimpleNamespace(
        content=list(blocks),
        usage=SimpleNamespace(input_tokens=100, output_tokens=50),
        stop_reason=stop_reason,
    )


def _text(text):
    return SimpleNamespace(type="text", text=text)


def _thinking():
    return SimpleNamespace(type="thinking", thinking="")


@pytest.fixture
def make_llm(monkeypatch):
    """Build an AnthropicLLM whose client replays the given responses/exceptions."""

    def factory(*replies):
        calls = []

        def create(**kwargs):
            calls.append(kwargs)
            reply = replies[len(calls) - 1]
            if isinstance(reply, Exception):
                raise reply
            return reply

        fake_anthropic = types.ModuleType("anthropic")
        fake_anthropic.Anthropic = lambda api_key: SimpleNamespace(
            messages=SimpleNamespace(create=create)
        )
        monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)
        monkeypatch.setattr(llm_module.time, "sleep", lambda seconds: None)
        return AnthropicLLM(api_key="unit-test-key"), calls

    return factory


@pytest.fixture
def rca_inputs():
    graph = ServiceGraph()
    graph.add_dependency(Dependency(from_service="api", to_service="db"))
    graph.add_dependency(Dependency(from_service="api", to_service="cache"))
    graph.add_incident(
        IncidentNode("db", IncidentType.ERROR_SPIKE, datetime(2025, 11, 10, tzinfo=timezone.utc))
    )
    candidates = [
        RootCauseCandidate(
            service="db",
            incident_type=IncidentType.ERROR_SPIKE,
            confidence=0.8,
            explanation="db errors",
            evidence=["Error: connection refused"],
            remediation=["Check db"],
        )
    ]
    return graph, candidates


def test_summarize_with_dependencies_and_thinking_block(make_llm, rca_inputs):
    """graph.dependencies is a set; slicing it raised TypeError for any graph with
    edges. The reply may also start with a thinking block before the text."""
    llm, calls = make_llm(_response(_thinking(), _text("## Executive Summary\nDB down")))
    graph, candidates = rca_inputs

    summary = llm.summarize_rca(graph, candidates, "API errors")

    assert summary == "## Executive Summary\nDB down"
    # The previous default, claude-3-5-sonnet-20241022, was retired and returns 404
    assert calls[0]["model"] == "claude-sonnet-5-5"
    prompt = calls[0]["messages"][0]["content"]
    assert prompt.index("api → cache") < prompt.index("api → db")
    assert llm.get_usage_stats()["total_tokens"] == 150
    assert llm.get_usage_stats()["total_cost_usd"] == pytest.approx(100 * 2e-6 + 50 * 10e-6)


def test_non_retryable_error_falls_back_without_retrying(make_llm, rca_inputs):
    llm, calls = make_llm(FakeAPIError(404))
    graph, candidates = rca_inputs

    summary = llm.summarize_rca(graph, candidates, "API errors")

    assert len(calls) == 1
    assert summary == DummyLLM().summarize_rca(graph, candidates, "API errors")


def test_transient_errors_are_retried(make_llm, rca_inputs):
    llm, calls = make_llm(FakeAPIError(529), FakeAPIError(429), _response(_text("ok")))
    graph, candidates = rca_inputs

    assert llm.summarize_rca(graph, candidates, "API errors") == "ok"
    assert len(calls) == 3


def test_response_without_text_falls_back(make_llm, rca_inputs):
    llm, calls = make_llm(_response(_thinking(), stop_reason="refusal"))
    graph, candidates = rca_inputs

    summary = llm.summarize_rca(graph, candidates, "API errors")

    assert len(calls) == 1
    assert summary.startswith("## RCA Summary: API errors")

import pytest

from agent.llm.prompt_builder import (
    SYSTEM_PROMPT,
    build_llm_prompt,
)
from agent.rag.context_builder import (
    RAGContext,
)


def _rag_context():
    return RAGContext(
        query="OOMKilled memory",
        context=(
            "[Context 1]\n"
            "Title: OOMKilled Runbook\n"
            "Category: sre\n"
            "Source: agent/knowledge/sre_runbooks.md\n"
            "Score: 1.0000\n"
            "Content:\n"
            "OOMKilled happens when a container "
            "exceeds its memory limit."
        ),
        results=tuple(),
        sources=(
            "agent/knowledge/sre_runbooks.md",
        ),
        empty=False,
        performs_write=False,
    )


def test_build_llm_prompt_with_rag_context():
    prompt = build_llm_prompt(
        query=(
            "Why was checkoutservice OOMKilled?"
        ),
        rag_context=_rag_context(),
        signal_type="sre_incident",
        namespace="default",
        workload_name="checkoutservice",
    )

    assert prompt.system_prompt == SYSTEM_PROMPT

    assert (
        "Signal type: sre_incident"
        in prompt.user_prompt
    )

    assert (
        "Namespace: default"
        in prompt.user_prompt
    )

    assert (
        "Workload: checkoutservice"
        in prompt.user_prompt
    )

    assert (
        "OOMKilled Runbook"
        in prompt.user_prompt
    )

    assert prompt.rag_context_used is True

    assert prompt.sources == (
        "agent/knowledge/sre_runbooks.md",
    )

    assert (
        prompt.requires_human_approval
        is True
    )

    assert (
        prompt.allows_direct_cluster_write
        is False
    )

    assert prompt.performs_write is False


def test_prompt_contains_safety_rules():
    prompt = build_llm_prompt(
        query="Analyze this incident.",
        rag_context=_rag_context(),
        signal_type="sre_incident",
    )

    assert (
        "Never modify Kubernetes resources directly"
        in prompt.system_prompt
    )

    assert (
        "Human approval is required"
        in prompt.system_prompt
    )

    assert (
        "GitOps is the source of truth"
        in prompt.system_prompt
    )

    assert (
        "Do not invent metrics"
        in prompt.system_prompt
    )


def test_empty_rag_context_is_supported():
    rag_context = RAGContext(
        query="unknown",
        context="",
        results=tuple(),
        sources=tuple(),
        empty=True,
        performs_write=False,
    )

    prompt = build_llm_prompt(
        query="Analyze unknown problem.",
        rag_context=rag_context,
        signal_type="sre_incident",
        namespace="default",
    )

    assert prompt.rag_context_used is False

    assert (
        "No relevant RAG context was found."
        in prompt.user_prompt
    )

    assert prompt.sources == tuple()


def test_finops_prompt():
    prompt = build_llm_prompt(
        query=(
            "Should this workload be rightsized?"
        ),
        rag_context=_rag_context(),
        signal_type="finops",
        namespace="default",
        workload_name="checkoutservice",
    )

    assert (
        "Signal type: finops"
        in prompt.user_prompt
    )

    assert (
        "Any configuration change must "
        "require human approval"
        in prompt.user_prompt
    )


def test_empty_query_is_rejected():
    with pytest.raises(
        ValueError,
        match="LLM query is required",
    ):
        build_llm_prompt(
            query="   ",
            rag_context=_rag_context(),
            signal_type="sre",
        )


def test_empty_signal_type_is_rejected():
    with pytest.raises(
        ValueError,
        match="signal_type is required",
    ):
        build_llm_prompt(
            query="Analyze this.",
            rag_context=_rag_context(),
            signal_type="   ",
        )
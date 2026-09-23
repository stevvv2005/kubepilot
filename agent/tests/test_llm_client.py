from dataclasses import replace

import pytest

from agent.llm.client import (
    MockLLMClient,
)
from agent.llm.prompt_builder import (
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
            "exceeds its configured memory limit."
        ),
        results=tuple(),
        sources=(
            "agent/knowledge/sre_runbooks.md",
        ),
        empty=False,
        performs_write=False,
    )


def _prompt():
    return build_llm_prompt(
        query=(
            "Why was checkoutservice OOMKilled?"
        ),
        rag_context=_rag_context(),
        signal_type="sre_incident",
        namespace="default",
        workload_name="checkoutservice",
    )


def test_mock_llm_client_generates_response():
    client = MockLLMClient()

    response = client.generate(
        _prompt()
    )

    assert response.provider == "mock"

    assert (
        response.model
        == "kubepilot-mock-v1"
    )

    assert (
        "KubePilot mock analysis"
        in response.content
    )

    assert (
        "GitOps"
        in response.content
    )

    assert (
        response.rag_context_used
        is True
    )

    assert response.sources == (
        "agent/knowledge/sre_runbooks.md",
    )

    assert (
        response.requires_human_approval
        is True
    )

    assert (
        response.allows_direct_cluster_write
        is False
    )

    assert (
        response.external_request_performed
        is False
    )

    assert response.performs_write is False


def test_mock_client_is_deterministic():
    client = MockLLMClient()

    first = client.generate(
        _prompt()
    )

    second = client.generate(
        _prompt()
    )

    assert first == second


def test_prompt_declaring_write_is_rejected():
    prompt = replace(
        _prompt(),
        performs_write=True,
    )

    client = MockLLMClient()

    with pytest.raises(
        ValueError,
        match="unexpectedly declares",
    ):
        client.generate(prompt)


def test_direct_cluster_write_is_rejected():
    prompt = replace(
        _prompt(),
        allows_direct_cluster_write=True,
    )

    client = MockLLMClient()

    with pytest.raises(
        ValueError,
        match=(
            "Direct Kubernetes writes "
            "are not allowed"
        ),
    ):
        client.generate(prompt)


def test_missing_human_approval_is_rejected():
    prompt = replace(
        _prompt(),
        requires_human_approval=False,
    )

    client = MockLLMClient()

    with pytest.raises(
        ValueError,
        match=(
            "must require human approval"
        ),
    ):
        client.generate(prompt)


def test_empty_system_prompt_is_rejected():
    prompt = replace(
        _prompt(),
        system_prompt="",
    )

    client = MockLLMClient()

    with pytest.raises(
        ValueError,
        match="system prompt is required",
    ):
        client.generate(prompt)


def test_empty_user_prompt_is_rejected():
    prompt = replace(
        _prompt(),
        user_prompt="",
    )

    client = MockLLMClient()

    with pytest.raises(
        ValueError,
        match="user prompt is required",
    ):
        client.generate(prompt)
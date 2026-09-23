from dataclasses import replace

import pytest

from agent.llm.bedrock_client import (
    BedrockLLMClient,
)
from agent.llm.prompt_builder import (
    build_llm_prompt,
)
from agent.rag.context_builder import (
    RAGContext,
)


MODEL_ID = "test-bedrock-model"


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


def _client():
    return BedrockLLMClient(
        model_id=MODEL_ID,
        region="eu-west-3",
        max_tokens=1024,
        temperature=0.2,
    )


def test_bedrock_dry_run_builds_request():
    client = _client()

    result = client.generate(
        _prompt(),
        dry_run=True,
    )

    assert (
        result.request.region
        == "eu-west-3"
    )

    assert (
        result.request.model_id
        == MODEL_ID
    )

    assert (
        result.request.max_tokens
        == 1024
    )

    assert (
        result.request.temperature
        == 0.2
    )

    assert result.request.dry_run is True

    assert (
        result.request.performs_write
        is False
    )


def test_bedrock_dry_run_response():
    client = _client()

    result = client.generate(
        _prompt()
    )

    response = result.response

    assert (
        response.provider
        == "aws-bedrock"
    )

    assert (
        response.model
        == MODEL_ID
    )

    assert (
        "dry-run"
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


def test_bedrock_dry_run_does_not_invoke_model():
    client = _client()

    result = client.generate(
        _prompt()
    )

    assert (
        result.would_invoke_model
        is True
    )

    assert (
        result.invoked_model
        is False
    )

    assert (
        result.external_request_performed
        is False
    )

    assert result.performs_write is False


def test_real_bedrock_invocation_is_disabled():
    client = _client()

    with pytest.raises(
        ValueError,
        match=(
            "Real Bedrock invocation "
            "is disabled"
        ),
    ):
        client.generate(
            _prompt(),
            dry_run=False,
        )


def test_missing_model_id_is_rejected():
    with pytest.raises(
        ValueError,
        match="model_id is required",
    ):
        BedrockLLMClient(
            model_id="   ",
        )


def test_missing_region_is_rejected():
    with pytest.raises(
        ValueError,
        match="region is required",
    ):
        BedrockLLMClient(
            model_id=MODEL_ID,
            region="   ",
        )


def test_invalid_max_tokens_is_rejected():
    with pytest.raises(
        ValueError,
        match="max_tokens",
    ):
        BedrockLLMClient(
            model_id=MODEL_ID,
            max_tokens=0,
        )


def test_invalid_temperature_is_rejected():
    with pytest.raises(
        ValueError,
        match="temperature",
    ):
        BedrockLLMClient(
            model_id=MODEL_ID,
            temperature=1.5,
        )


def test_prompt_declaring_write_is_rejected():
    prompt = replace(
        _prompt(),
        performs_write=True,
    )

    with pytest.raises(
        ValueError,
        match="unexpectedly declares",
    ):
        _client().generate(
            prompt
        )


def test_direct_cluster_write_is_rejected():
    prompt = replace(
        _prompt(),
        allows_direct_cluster_write=True,
    )

    with pytest.raises(
        ValueError,
        match=(
            "Direct Kubernetes writes "
            "are not allowed"
        ),
    ):
        _client().generate(
            prompt
        )


def test_missing_human_approval_is_rejected():
    prompt = replace(
        _prompt(),
        requires_human_approval=False,
    )

    with pytest.raises(
        ValueError,
        match=(
            "must require human approval"
        ),
    ):
        _client().generate(
            prompt
        )


def test_empty_system_prompt_is_rejected():
    prompt = replace(
        _prompt(),
        system_prompt="",
    )

    with pytest.raises(
        ValueError,
        match="system prompt is required",
    ):
        _client().generate(
            prompt
        )


def test_empty_user_prompt_is_rejected():
    prompt = replace(
        _prompt(),
        user_prompt="",
    )

    with pytest.raises(
        ValueError,
        match="user prompt is required",
    ):
        _client().generate(
            prompt
        )
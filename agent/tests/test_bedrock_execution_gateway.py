import pytest

from agent.llm.bedrock_client import (
    BedrockLLMClient,
)
from agent.llm.bedrock_execution_gateway import (
    validate_bedrock_execution,
)
from agent.llm.prompt_builder import (
    LLMPrompt,
)


def _prompt():
    return LLMPrompt(
        system_prompt="system",
        user_prompt="user",
        rag_context_used=False,
        sources=tuple(),
        requires_human_approval=True,
        allows_direct_cluster_write=False,
        performs_write=False,
    )


def test_dry_run_request_is_rejected():
    client = BedrockLLMClient(
        model_id="amazon.nova-micro-v1:0",
    )

    request = client.build_request(
        _prompt(),
        dry_run=True,
    )

    result = validate_bedrock_execution(
        prompt=_prompt(),
        request=request,
        live_authorized=True,
    )

    assert result.allowed is False
    assert result.ready_to_invoke is False
    assert (
        result.external_request_allowed
        is False
    )


def test_live_request_without_authorization_is_rejected():
    client = BedrockLLMClient(
        model_id="amazon.nova-micro-v1:0",
    )

    request = client.build_request(
        _prompt(),
        dry_run=False,
    )

    result = validate_bedrock_execution(
        prompt=_prompt(),
        request=request,
        live_authorized=False,
    )

    assert result.allowed is False
    assert result.ready_to_invoke is False


def test_live_request_with_authorization_is_allowed():
    client = BedrockLLMClient(
        model_id="amazon.nova-micro-v1:0",
    )

    request = client.build_request(
        _prompt(),
        dry_run=False,
    )

    result = validate_bedrock_execution(
        prompt=_prompt(),
        request=request,
        live_authorized=True,
    )

    assert result.allowed is True
    assert result.ready_to_invoke is True
    assert (
        result.external_request_allowed
        is True
    )

    assert result.performs_write is False


def test_prompt_direct_cluster_write_is_rejected():
    unsafe_prompt = LLMPrompt(
        system_prompt="system",
        user_prompt="user",
        rag_context_used=False,
        sources=tuple(),
        requires_human_approval=True,
        allows_direct_cluster_write=True,
        performs_write=False,
    )

    client = BedrockLLMClient(
        model_id="amazon.nova-micro-v1:0",
    )

    request = client.build_request(
        _prompt(),
        dry_run=False,
    )

    with pytest.raises(
        ValueError,
        match="Direct Kubernetes writes",
    ):
        validate_bedrock_execution(
            prompt=unsafe_prompt,
            request=request,
            live_authorized=True,
        )


def test_missing_human_approval_is_rejected():
    unsafe_prompt = LLMPrompt(
        system_prompt="system",
        user_prompt="user",
        rag_context_used=False,
        sources=tuple(),
        requires_human_approval=False,
        allows_direct_cluster_write=False,
        performs_write=False,
    )

    client = BedrockLLMClient(
        model_id="amazon.nova-micro-v1:0",
    )

    request = client.build_request(
        _prompt(),
        dry_run=False,
    )

    with pytest.raises(
        ValueError,
        match="must require human approval",
    ):
        validate_bedrock_execution(
            prompt=unsafe_prompt,
            request=request,
            live_authorized=True,
        )
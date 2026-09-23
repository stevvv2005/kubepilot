from dataclasses import replace

import pytest

from agent.llm.bedrock_client import (
    BedrockLLMClient,
)
from agent.llm.bedrock_runtime import (
    BedrockRuntimeAdapter,
)
from agent.llm.prompt_builder import (
    build_llm_prompt,
)
from agent.rag.context_builder import (
    RAGContext,
)


MODEL_ID = "test-bedrock-model"


class FakeBedrockRuntimeClient:
    def __init__(self):
        self.calls = []

    def converse(
        self,
        **kwargs,
    ):
        self.calls.append(
            kwargs
        )

        return {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "text": (
                                "The workload exceeded "
                                "its memory limit. "
                                "Review the GitOps "
                                "configuration and require "
                                "human approval."
                            ),
                        }
                    ],
                }
            },
            "usage": {
                "inputTokens": 120,
                "outputTokens": 35,
            },
            "stopReason": "end_turn",
        }


def _rag_context():
    return RAGContext(
        query="OOMKilled memory",
        context=(
            "[Context 1]\n"
            "Title: OOMKilled Runbook\n"
            "Category: sre\n"
            "Source: agent/knowledge/"
            "sre_runbooks.md\n"
            "Score: 1.0000\n"
            "Content:\n"
            "OOMKilled happens when a container "
            "exceeds its configured memory limit."
        ),
        results=tuple(),
        sources=(
            "agent/knowledge/"
            "sre_runbooks.md",
        ),
        empty=False,
        performs_write=False,
    )


def _prompt():
    return build_llm_prompt(
        query=(
            "Why was checkoutservice "
            "OOMKilled?"
        ),
        rag_context=_rag_context(),
        signal_type="sre_incident",
        namespace="default",
        workload_name="checkoutservice",
    )


def _request():
    client = BedrockLLMClient(
        model_id=MODEL_ID,
        region="eu-west-3",
        max_tokens=1024,
        temperature=0.2,
    )

    return client.build_request(
        _prompt(),
        dry_run=True,
    )


def test_runtime_adapter_invokes_injected_client():
    fake = FakeBedrockRuntimeClient()

    adapter = BedrockRuntimeAdapter(
        runtime_client=fake,
        external_request_performed=False,
    )

    result = adapter.invoke(
        prompt=_prompt(),
        request=_request(),
    )

    assert result.runtime_invoked is True

    assert (
        result.external_request_performed
        is False
    )

    assert len(fake.calls) == 1


def test_runtime_request_shape():
    fake = FakeBedrockRuntimeClient()

    adapter = BedrockRuntimeAdapter(
        runtime_client=fake,
    )

    adapter.invoke(
        prompt=_prompt(),
        request=_request(),
    )

    call = fake.calls[0]

    assert (
        call["modelId"]
        == MODEL_ID
    )

    assert (
        call["system"][0]["text"]
        == _prompt().system_prompt
    )

    assert (
        call["messages"][0]["role"]
        == "user"
    )

    assert (
        call["messages"][0]
        ["content"][0]
        ["text"]
        == _prompt().user_prompt
    )

    assert (
        call["inferenceConfig"]
        ["maxTokens"]
        == 1024
    )

    assert (
        call["inferenceConfig"]
        ["temperature"]
        == 0.2
    )


def test_runtime_response_is_parsed():
    fake = FakeBedrockRuntimeClient()

    result = BedrockRuntimeAdapter(
        runtime_client=fake,
    ).invoke(
        prompt=_prompt(),
        request=_request(),
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
        "memory limit"
        in response.content
    )

    assert response.rag_context_used is True

    assert response.sources == (
        "agent/knowledge/"
        "sre_runbooks.md",
    )

    assert (
        response.requires_human_approval
        is True
    )

    assert (
        response.allows_direct_cluster_write
        is False
    )

    assert response.performs_write is False


def test_runtime_usage_is_exposed():
    fake = FakeBedrockRuntimeClient()

    result = BedrockRuntimeAdapter(
        runtime_client=fake,
    ).invoke(
        prompt=_prompt(),
        request=_request(),
    )

    assert result.input_tokens == 120
    assert result.output_tokens == 35

    assert (
        result.stop_reason
        == "end_turn"
    )


def test_external_request_flag_can_be_enabled():
    fake = FakeBedrockRuntimeClient()

    result = BedrockRuntimeAdapter(
        runtime_client=fake,
        external_request_performed=True,
    ).invoke(
        prompt=_prompt(),
        request=_request(),
    )

    assert (
        result.external_request_performed
        is True
    )

    assert (
        result.response
        .external_request_performed
        is True
    )


def test_prompt_write_is_rejected():
    prompt = replace(
        _prompt(),
        performs_write=True,
    )

    adapter = BedrockRuntimeAdapter(
        runtime_client=(
            FakeBedrockRuntimeClient()
        ),
    )

    with pytest.raises(
        ValueError,
        match="unexpectedly declares",
    ):
        adapter.invoke(
            prompt=prompt,
            request=_request(),
        )


def test_direct_cluster_write_is_rejected():
    prompt = replace(
        _prompt(),
        allows_direct_cluster_write=True,
    )

    adapter = BedrockRuntimeAdapter(
        runtime_client=(
            FakeBedrockRuntimeClient()
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "Direct Kubernetes writes "
            "are not allowed"
        ),
    ):
        adapter.invoke(
            prompt=prompt,
            request=_request(),
        )


def test_request_write_is_rejected():
    request = replace(
        _request(),
        performs_write=True,
    )

    adapter = BedrockRuntimeAdapter(
        runtime_client=(
            FakeBedrockRuntimeClient()
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "Bedrock request unexpectedly "
            "declares"
        ),
    ):
        adapter.invoke(
            prompt=_prompt(),
            request=request,
        )


def test_invalid_runtime_response_is_rejected():
    class InvalidClient:
        def converse(
            self,
            **kwargs,
        ):
            return {
                "output": {}
            }

    adapter = BedrockRuntimeAdapter(
        runtime_client=InvalidClient(),
    )

    with pytest.raises(
        ValueError,
        match=(
            "valid output message"
        ),
    ):
        adapter.invoke(
            prompt=_prompt(),
            request=_request(),
        )


def test_empty_runtime_text_is_rejected():
    class EmptyClient:
        def converse(
            self,
            **kwargs,
        ):
            return {
                "output": {
                    "message": {
                        "content": [
                            {
                                "text": "   "
                            }
                        ]
                    }
                }
            }

    adapter = BedrockRuntimeAdapter(
        runtime_client=EmptyClient(),
    )

    with pytest.raises(
        ValueError,
        match="contains no text",
    ):
        adapter.invoke(
            prompt=_prompt(),
            request=_request(),
        )
from dataclasses import replace

import pytest

from agent.llm.client import (
    LLMResponse,
    MockLLMClient,
)
from agent.llm.workflow import (
    build_default_knowledge_base,
    run_llm_workflow,
)
from agent.rag.knowledge_base import (
    KnowledgeBase,
)
from agent.rag.models import (
    KnowledgeDocument,
)


def _knowledge_base():
    documents = (
        KnowledgeDocument(
            document_id="oom",
            title="OOMKilled Runbook",
            category="sre",
            content=(
                "OOMKilled indicates that a container "
                "exceeded its configured memory limit. "
                "Review memory usage and prepare changes "
                "through GitOps with human approval."
            ),
            source="memory:sre",
        ),
        KnowledgeDocument(
            document_id="finops",
            title="FinOps Rightsizing",
            category="finops",
            content=(
                "Rightsizing should compare CPU and "
                "memory utilization against requests. "
                "Production decisions should use "
                "historical p95 or p99 metrics."
            ),
            source="memory:finops",
        ),
    )

    return KnowledgeBase.from_documents(
        documents,
        max_words=100,
    )


def test_sre_llm_workflow():
    result = run_llm_workflow(
        client=MockLLMClient(),
        query=(
            "Why was the container OOMKilled "
            "after exceeding its memory limit?"
        ),
        signal_type="sre_incident",
        namespace="default",
        workload_name="checkoutservice",
        knowledge_base=_knowledge_base(),
    )

    assert (
        result.signal_type
        == "sre_incident"
    )

    assert result.namespace == "default"

    assert (
        result.workload_name
        == "checkoutservice"
    )

    assert result.rag_context.empty is False

    assert result.prompt.rag_context_used is True

    assert (
        result.response.provider
        == "mock"
    )

    assert (
    "GitOps"
    in result.structured_output.recommendation
    )

    assert (
        result.requires_human_approval
        is True
    )

    assert (
        result.allows_direct_cluster_write
        is False
    )

    assert (
        result.external_request_performed
        is False
    )

    assert result.performs_write is False


def test_finops_llm_workflow():
    result = run_llm_workflow(
        client=MockLLMClient(),
        query=(
            "Should this workload be rightsized "
            "based on CPU memory utilization?"
        ),
        signal_type="finops",
        namespace="default",
        workload_name="checkoutservice",
        knowledge_base=_knowledge_base(),
    )
    assert (
    result.structured_output
    .requires_human_approval
    is True
    )

    assert (
    result.structured_output
    .allows_direct_cluster_write
    is False
    )

    assert (
    result.structured_output
    .performs_write
    is False
    )
    assert (
        result.signal_type
        == "finops"
    )

    assert (
        "FinOps Rightsizing"
        in result.rag_context.context
    )

    assert (
        "Signal type: finops"
        in result.prompt.user_prompt
    )

    assert (
        result.response
        .external_request_performed
        is False
    )


def test_workflow_without_matching_rag_context():
    result = run_llm_workflow(
        client=MockLLMClient(),
        query="unknown xyz abc",
        signal_type="sre_incident",
        knowledge_base=_knowledge_base(),
    )

    assert result.rag_context.empty is True

    assert (
        result.prompt.rag_context_used
        is False
    )

    assert (
        "No relevant RAG context was found."
        in result.prompt.user_prompt
    )


def test_empty_query_is_rejected():
    with pytest.raises(
        ValueError,
        match="query is required",
    ):
        run_llm_workflow(
            client=MockLLMClient(),
            query="   ",
            signal_type="sre",
            knowledge_base=_knowledge_base(),
        )


def test_empty_signal_type_is_rejected():
    with pytest.raises(
        ValueError,
        match="signal_type is required",
    ):
        run_llm_workflow(
            client=MockLLMClient(),
            query="OOMKilled memory",
            signal_type="   ",
            knowledge_base=_knowledge_base(),
        )


def test_invalid_top_k_is_rejected():
    with pytest.raises(
        ValueError,
        match="top_k",
    ):
        run_llm_workflow(
            client=MockLLMClient(),
            query="OOMKilled memory",
            signal_type="sre",
            knowledge_base=_knowledge_base(),
            top_k=0,
        )


def test_write_declaring_llm_response_is_rejected():
    class UnsafeClient:
        def generate(
            self,
            prompt,
        ):
            return LLMResponse(
                provider="unsafe",
                model="unsafe",
                content="unsafe",
                rag_context_used=(
                    prompt.rag_context_used
                ),
                sources=prompt.sources,
                requires_human_approval=True,
                allows_direct_cluster_write=False,
                external_request_performed=False,
                performs_write=True,
            )

    with pytest.raises(
        ValueError,
        match="response unexpectedly declares",
    ):
        run_llm_workflow(
            client=UnsafeClient(),
            query="OOMKilled memory",
            signal_type="sre",
            knowledge_base=_knowledge_base(),
        )


def test_direct_write_llm_response_is_rejected():
    class UnsafeClient:
        def generate(
            self,
            prompt,
        ):
            return LLMResponse(
                provider="unsafe",
                model="unsafe",
                content="unsafe",
                rag_context_used=(
                    prompt.rag_context_used
                ),
                sources=prompt.sources,
                requires_human_approval=True,
                allows_direct_cluster_write=True,
                external_request_performed=False,
                performs_write=False,
            )

    with pytest.raises(
        ValueError,
        match="cannot allow direct",
    ):
        run_llm_workflow(
            client=UnsafeClient(),
            query="OOMKilled memory",
            signal_type="sre",
            knowledge_base=_knowledge_base(),
        )


def test_missing_human_approval_is_rejected():
    class UnsafeClient:
        def generate(
            self,
            prompt,
        ):
            return LLMResponse(
                provider="unsafe",
                model="unsafe",
                content="unsafe",
                rag_context_used=(
                    prompt.rag_context_used
                ),
                sources=prompt.sources,
                requires_human_approval=False,
                allows_direct_cluster_write=False,
                external_request_performed=False,
                performs_write=False,
            )

    with pytest.raises(
        ValueError,
        match="must require human approval",
    ):
        run_llm_workflow(
            client=UnsafeClient(),
            query="OOMKilled memory",
            signal_type="sre",
            knowledge_base=_knowledge_base(),
        )


def test_default_knowledge_base_loads_repo_runbooks():
    kb = build_default_knowledge_base(
        repository_root=".",
    )

    assert len(kb.chunks) > 0

    sre_results = kb.search(
        "OOMKilled memory limit",
        top_k=2,
    )

    finops_results = kb.search(
        "rightsizing utilization p95",
        top_k=2,
    )

    assert len(sre_results) >= 1
    assert len(finops_results) >= 1
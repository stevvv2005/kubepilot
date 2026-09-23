import pytest

from agent.rag.context_builder import (
    build_rag_context,
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
                "OOMKilled happens when a container "
                "exceeds its configured memory limit. "
                "Review memory usage and memory limits "
                "before preparing a GitOps change."
            ),
            source=(
                "agent/knowledge/"
                "sre_runbooks.md"
            ),
        ),
        KnowledgeDocument(
            document_id="image",
            title="ImagePullBackOff Runbook",
            category="sre",
            content=(
                "ImagePullBackOff means Kubernetes "
                "cannot pull the requested image. "
                "Verify the image repository and tag."
            ),
            source=(
                "agent/knowledge/"
                "sre_runbooks.md"
            ),
        ),
        KnowledgeDocument(
            document_id="finops",
            title="FinOps Rightsizing",
            category="finops",
            content=(
                "Rightsizing should compare resource "
                "usage with requests and use historical "
                "metrics before production changes."
            ),
            source=(
                "agent/knowledge/"
                "finops_runbooks.md"
            ),
        ),
    )

    return KnowledgeBase.from_documents(
        documents,
        max_words=100,
    )


def test_build_rag_context():
    kb = _knowledge_base()

    result = build_rag_context(
        kb,
        query="container memory limit",
        top_k=2,
    )

    assert result.query == (
        "container memory limit"
    )

    assert result.empty is False

    assert len(result.results) >= 1

    assert (
        "OOMKilled Runbook"
        in result.context
    )

    assert (
        "memory limit"
        in result.context
    )

    assert (
        "agent/knowledge/sre_runbooks.md"
        in result.sources
    )

    assert result.performs_write is False


def test_context_contains_metadata():
    kb = _knowledge_base()

    result = build_rag_context(
        kb,
        query="image repository tag",
        top_k=1,
    )

    assert "[Context 1]" in result.context
    assert "Title:" in result.context
    assert "Category:" in result.context
    assert "Source:" in result.context
    assert "Score:" in result.context
    assert "Content:" in result.context


def test_sources_are_deduplicated():
    documents = (
        KnowledgeDocument(
            document_id="doc-1",
            title="One",
            category="sre",
            content="memory limit container",
            source="same.md",
        ),
        KnowledgeDocument(
            document_id="doc-2",
            title="Two",
            category="sre",
            content="memory usage container",
            source="same.md",
        ),
    )

    kb = KnowledgeBase.from_documents(
        documents,
    )

    result = build_rag_context(
        kb,
        query="memory container",
        top_k=2,
    )

    assert result.sources == (
        "same.md",
    )


def test_unknown_query_returns_empty_context():
    kb = _knowledge_base()

    result = build_rag_context(
        kb,
        query="completely unrelated xyz",
    )

    assert result.empty is True
    assert result.context == ""
    assert result.results == tuple()
    assert result.sources == tuple()
    assert result.performs_write is False


def test_empty_query_is_rejected():
    kb = _knowledge_base()

    with pytest.raises(
        ValueError,
        match="RAG query is required",
    ):
        build_rag_context(
            kb,
            query="   ",
        )


def test_invalid_top_k_is_rejected():
    kb = _knowledge_base()

    with pytest.raises(
        ValueError,
        match="top_k",
    ):
        build_rag_context(
            kb,
            query="memory",
            top_k=0,
        )
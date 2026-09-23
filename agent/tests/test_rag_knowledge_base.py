from pathlib import Path

import pytest

from agent.rag.chunker import (
    chunk_document,
)
from agent.rag.knowledge_base import (
    KnowledgeBase,
    load_markdown_document,
)
from agent.rag.models import (
    KnowledgeDocument,
)


def test_chunk_document():
    document = KnowledgeDocument(
        document_id="doc-1",
        title="Test",
        category="sre",
        content=(
            "one two three four five six"
        ),
        source="memory",
    )

    chunks = chunk_document(
        document,
        max_words=2,
    )

    assert len(chunks) == 3

    assert chunks[0].text == "one two"
    assert chunks[1].text == "three four"
    assert chunks[2].text == "five six"


def test_empty_document_returns_no_chunks():
    document = KnowledgeDocument(
        document_id="doc-1",
        title="Empty",
        category="sre",
        content="   ",
        source="memory",
    )

    assert (
        chunk_document(document)
        == tuple()
    )


def test_invalid_chunk_size():
    document = KnowledgeDocument(
        document_id="doc-1",
        title="Test",
        category="sre",
        content="hello",
        source="memory",
    )

    with pytest.raises(
        ValueError,
        match="max_words",
    ):
        chunk_document(
            document,
            max_words=0,
        )


def test_knowledge_base_search():
    documents = (
        KnowledgeDocument(
            document_id="oom",
            title="OOMKilled",
            category="sre",
            content=(
                "OOMKilled happens when a "
                "container exceeds memory limit."
            ),
            source="memory",
        ),
        KnowledgeDocument(
            document_id="image",
            title="ImagePullBackOff",
            category="sre",
            content=(
                "ImagePullBackOff occurs when "
                "Kubernetes cannot pull an image."
            ),
            source="memory",
        ),
    )

    kb = KnowledgeBase.from_documents(
        documents,
        max_words=100,
    )

    results = kb.search(
        "container memory limit",
        top_k=1,
    )

    assert len(results) == 1

    assert (
        results[0].chunk.document_id
        == "oom"
    )

    assert results[0].score > 0


def test_search_unknown_query_returns_empty():
    document = KnowledgeDocument(
        document_id="oom",
        title="OOMKilled",
        category="sre",
        content="memory container kubernetes",
        source="memory",
    )

    kb = KnowledgeBase.from_documents(
        (document,),
    )

    results = kb.search(
        "completely unrelated words",
    )

    assert results == tuple()


def test_invalid_top_k():
    kb = KnowledgeBase(
        tuple()
    )

    with pytest.raises(
        ValueError,
        match="top_k",
    ):
        kb.search(
            "test",
            top_k=0,
        )


def test_load_markdown_document(
    tmp_path: Path,
):
    file_path = (
        tmp_path
        / "runbook.md"
    )

    file_path.write_text(
        "# Runbook\nOOMKilled memory",
        encoding="utf-8",
    )

    document = load_markdown_document(
        file_path,
        document_id="runbook",
        title="Runbook",
        category="sre",
    )

    assert (
        document.document_id
        == "runbook"
    )

    assert (
        "OOMKilled"
        in document.content
    )


def test_load_missing_document():
    with pytest.raises(
        FileNotFoundError,
    ):
        load_markdown_document(
            Path(
                "does-not-exist.md"
            ),
            document_id="missing",
            title="Missing",
            category="sre",
        )
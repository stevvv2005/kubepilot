from dataclasses import dataclass

from agent.rag.knowledge_base import (
    KnowledgeBase,
)
from agent.rag.models import (
    SearchResult,
)


@dataclass(frozen=True)
class RAGContext:
    query: str

    context: str

    results: tuple[
        SearchResult,
        ...
    ]

    sources: tuple[
        str,
        ...
    ]

    empty: bool

    performs_write: bool = False


def build_rag_context(
    knowledge_base: KnowledgeBase,
    *,
    query: str,
    top_k: int = 3,
) -> RAGContext:
    """
    Retrieve relevant knowledge chunks and
    assemble a deterministic RAG context.

    No LLM or network request is performed.
    """

    normalized_query = query.strip()

    if not normalized_query:
        raise ValueError(
            "RAG query is required."
        )

    if top_k <= 0:
        raise ValueError(
            "top_k must be greater than zero."
        )

    results = knowledge_base.search(
        normalized_query,
        top_k=top_k,
    )

    if not results:
        return RAGContext(
            query=normalized_query,
            context="",
            results=tuple(),
            sources=tuple(),
            empty=True,
            performs_write=False,
        )

    context_parts = []
    sources = []

    for index, result in enumerate(
        results,
        start=1,
    ):
        chunk = result.chunk

        context_parts.append(
            (
                f"[Context {index}]\n"
                f"Title: {chunk.title}\n"
                f"Category: {chunk.category}\n"
                f"Source: {chunk.source}\n"
                f"Score: {result.score:.4f}\n"
                f"Content:\n{chunk.text}"
            )
        )

        if chunk.source not in sources:
            sources.append(
                chunk.source
            )

    context = "\n\n".join(
        context_parts
    )

    return RAGContext(
        query=normalized_query,
        context=context,
        results=results,
        sources=tuple(sources),
        empty=False,
        performs_write=False,
    )
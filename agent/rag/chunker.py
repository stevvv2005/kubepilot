from agent.rag.models import (
    KnowledgeChunk,
    KnowledgeDocument,
)


def chunk_document(
    document: KnowledgeDocument,
    *,
    max_words: int = 120,
) -> tuple[KnowledgeChunk, ...]:
    if max_words <= 0:
        raise ValueError(
            "max_words must be greater than zero."
        )

    content = document.content.strip()

    if not content:
        return tuple()

    words = content.split()

    chunks = []

    for index in range(
        0,
        len(words),
        max_words,
    ):
        chunk_words = words[
            index:index + max_words
        ]

        chunk_number = (
            index // max_words
        )

        chunks.append(
            KnowledgeChunk(
                chunk_id=(
                    f"{document.document_id}-"
                    f"{chunk_number}"
                ),
                document_id=(
                    document.document_id
                ),
                title=document.title,
                category=document.category,
                text=" ".join(chunk_words),
                source=document.source,
            )
        )

    return tuple(chunks)
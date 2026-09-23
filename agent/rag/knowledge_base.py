import re
from pathlib import Path

from agent.rag.chunker import (
    chunk_document,
)
from agent.rag.models import (
    KnowledgeChunk,
    KnowledgeDocument,
    SearchResult,
)


_TOKEN_PATTERN = re.compile(
    r"[a-zA-Z0-9_.:/-]+"
)


def _tokenize(
    text: str,
) -> set[str]:
    return {
        token.lower()
        for token
        in _TOKEN_PATTERN.findall(text)
    }


def _score_chunk(
    query: str,
    chunk: KnowledgeChunk,
) -> float:
    query_tokens = _tokenize(query)

    if not query_tokens:
        return 0.0

    chunk_tokens = _tokenize(
        chunk.text
    )

    if not chunk_tokens:
        return 0.0

    overlap = (
        query_tokens
        & chunk_tokens
    )

    return (
        len(overlap)
        / len(query_tokens)
    )


class KnowledgeBase:
    def __init__(
        self,
        chunks: tuple[
            KnowledgeChunk,
            ...
        ],
    ) -> None:
        self._chunks = chunks

    @property
    def chunks(
        self,
    ) -> tuple[
        KnowledgeChunk,
        ...
    ]:
        return self._chunks

    @classmethod
    def from_documents(
        cls,
        documents: tuple[
            KnowledgeDocument,
            ...
        ],
        *,
        max_words: int = 120,
    ) -> "KnowledgeBase":
        all_chunks = []

        for document in documents:
            all_chunks.extend(
                chunk_document(
                    document,
                    max_words=max_words,
                )
            )

        return cls(
            tuple(all_chunks)
        )

    def search(
        self,
        query: str,
        *,
        top_k: int = 3,
    ) -> tuple[
        SearchResult,
        ...
    ]:
        if top_k <= 0:
            raise ValueError(
                "top_k must be "
                "greater than zero."
            )

        scored_results = []

        for chunk in self._chunks:
            score = _score_chunk(
                query,
                chunk,
            )

            if score <= 0:
                continue

            scored_results.append(
                SearchResult(
                    chunk=chunk,
                    score=score,
                )
            )

        scored_results.sort(
            key=lambda result: (
                result.score
            ),
            reverse=True,
        )

        return tuple(
            scored_results[:top_k]
        )


def load_markdown_document(
    path: Path,
    *,
    document_id: str,
    title: str,
    category: str,
) -> KnowledgeDocument:
    if not path.exists():
        raise FileNotFoundError(
            f"Knowledge file not found: {path}"
        )

    content = path.read_text(
        encoding="utf-8",
    )

    return KnowledgeDocument(
        document_id=document_id,
        title=title,
        category=category,
        content=content,
        source=str(path),
    )
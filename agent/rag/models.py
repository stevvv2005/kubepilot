from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeDocument:
    document_id: str
    title: str
    category: str
    content: str
    source: str


@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_id: str
    document_id: str
    title: str
    category: str
    text: str
    source: str


@dataclass(frozen=True)
class SearchResult:
    chunk: KnowledgeChunk
    score: float
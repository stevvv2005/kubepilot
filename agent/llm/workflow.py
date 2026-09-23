from dataclasses import dataclass
from pathlib import Path

from agent.llm.client import (
    LLMClient,
    LLMResponse,
)
from agent.llm.prompt_builder import (
    LLMPrompt,
    build_llm_prompt,
)
from agent.rag.context_builder import (
    RAGContext,
    build_rag_context,
)
from agent.rag.knowledge_base import (
    KnowledgeBase,
    load_markdown_document,
)
from agent.llm.provider_selector import (
    LLMProviderSelection,
    generate_with_selected_provider,
)

@dataclass(frozen=True)
class LLMWorkflowResult:
    signal_type: str
    query: str

    namespace: str | None
    workload_name: str | None

    rag_context: RAGContext
    prompt: LLMPrompt
    response: LLMResponse

    requires_human_approval: bool
    allows_direct_cluster_write: bool

    external_request_performed: bool
    performs_write: bool = False


def build_default_knowledge_base(
    *,
    repository_root: str | Path = ".",
) -> KnowledgeBase:
    root = Path(repository_root).resolve()

    sre_path = (
        root
        / "agent"
        / "knowledge"
        / "sre_runbooks.md"
    )

    finops_path = (
        root
        / "agent"
        / "knowledge"
        / "finops_runbooks.md"
    )

    documents = (
        load_markdown_document(
            sre_path,
            document_id="sre-runbooks",
            title="KubePilot SRE Runbooks",
            category="sre",
        ),
        load_markdown_document(
            finops_path,
            document_id="finops-runbooks",
            title="KubePilot FinOps Runbooks",
            category="finops",
        ),
    )

    return KnowledgeBase.from_documents(
        documents,
        max_words=120,
    )


def run_llm_workflow(
    *,
    client: LLMClient | None = None,
    provider_selection: LLMProviderSelection | None = None,
    query: str,
    signal_type: str,
    namespace: str | None = None,
    workload_name: str | None = None,
    knowledge_base: KnowledgeBase | None = None,
    repository_root: str | Path = ".",
    top_k: int = 3,
) -> LLMWorkflowResult:
    normalized_query = query.strip()
    normalized_signal_type = signal_type.strip()

    if not normalized_query:
        raise ValueError(
            "LLM workflow query is required."
        )

    if not normalized_signal_type:
        raise ValueError(
            "LLM workflow signal_type is required."
        )

    if top_k <= 0:
        raise ValueError(
            "LLM workflow top_k must be greater than zero."
        )

    resolved_knowledge_base = (
        knowledge_base
        if knowledge_base is not None
        else build_default_knowledge_base(
            repository_root=repository_root,
        )
    )

    rag_context = build_rag_context(
        resolved_knowledge_base,
        query=normalized_query,
        top_k=top_k,
    )

    prompt = build_llm_prompt(
        query=normalized_query,
        rag_context=rag_context,
        signal_type=normalized_signal_type,
        namespace=namespace,
        workload_name=workload_name,
    )

    if client is not None and provider_selection is not None:
         raise ValueError(
        "Provide either client or provider_selection, "
        "not both."
          )

    if client is None and provider_selection is None:
        raise ValueError(
        "An LLM client or provider_selection "
        "is required."
    )

    if client is not None:
        response = client.generate(
        prompt
    )
    else:
        response = generate_with_selected_provider(
        prompt=prompt,
        selection=provider_selection,
    )

    if response.performs_write:
        raise ValueError(
            "LLM response unexpectedly declares "
            "a write operation."
        )

    if response.allows_direct_cluster_write:
        raise ValueError(
            "LLM response cannot allow direct "
            "Kubernetes writes."
        )

    if not response.requires_human_approval:
        raise ValueError(
            "LLM response must require human approval."
        )

    return LLMWorkflowResult(
        signal_type=normalized_signal_type,
        query=normalized_query,
        namespace=namespace,
        workload_name=workload_name,
        rag_context=rag_context,
        prompt=prompt,
        response=response,
        requires_human_approval=True,
        allows_direct_cluster_write=False,
        external_request_performed=(
            response.external_request_performed
        ),
        performs_write=False,
    )
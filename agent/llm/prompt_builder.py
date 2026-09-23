from dataclasses import dataclass

from agent.rag.context_builder import (
    RAGContext,
)


@dataclass(frozen=True)
class LLMPrompt:
    system_prompt: str
    user_prompt: str

    rag_context_used: bool
    sources: tuple[str, ...]

    requires_human_approval: bool
    allows_direct_cluster_write: bool
    performs_write: bool = False


SYSTEM_PROMPT = """
You are KubePilot, an AI SRE and FinOps assistant.

Your role is to analyze Kubernetes operational and cost signals
and produce safe, explainable recommendations.

Safety rules:

- Never modify Kubernetes resources directly.
- Never execute kubectl apply, patch, delete, or equivalent actions.
- Never auto-apply infrastructure changes.
- GitOps is the source of truth.
- Any configuration change must be prepared through Git.
- Human approval is required before a proposed change proceeds.
- Prefer evidence from the provided RAG context.
- If the provided context is insufficient, say so explicitly.
- Do not invent metrics, incidents, costs, or configuration values.
- Distinguish observed evidence from recommendations.
""".strip()


def build_llm_prompt(
    *,
    query: str,
    rag_context: RAGContext,
    signal_type: str,
    namespace: str | None = None,
    workload_name: str | None = None,
) -> LLMPrompt:
    normalized_query = query.strip()
    normalized_signal_type = signal_type.strip()

    if not normalized_query:
        raise ValueError(
            "LLM query is required."
        )

    if not normalized_signal_type:
        raise ValueError(
            "signal_type is required."
        )

    namespace_value = (
        namespace.strip()
        if namespace
        else "N/A"
    )

    workload_value = (
        workload_name.strip()
        if workload_name
        else "N/A"
    )

    if rag_context.empty:
        context_section = (
            "No relevant RAG context was found."
        )
    else:
        context_section = rag_context.context

    user_prompt = (
        f"Signal type: {normalized_signal_type}\n"
        f"Namespace: {namespace_value}\n"
        f"Workload: {workload_value}\n\n"
        f"User query:\n"
        f"{normalized_query}\n\n"
        f"Retrieved knowledge context:\n"
        f"{context_section}\n\n"
        "Instructions:\n"
        "- Analyze the signal using the available evidence.\n"
        "- Explain the likely cause or optimization opportunity.\n"
        "- Provide a safe recommendation.\n"
        "- Mention uncertainty when evidence is incomplete.\n"
        "- Do not propose direct Kubernetes mutation.\n"
        "- Any configuration change must require human approval.\n"
        "- Prefer a GitOps-based remediation path."
    )

    return LLMPrompt(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        rag_context_used=(
            not rag_context.empty
        ),
        sources=rag_context.sources,
        requires_human_approval=True,
        allows_direct_cluster_write=False,
        performs_write=False,
    )
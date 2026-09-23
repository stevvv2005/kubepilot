from dataclasses import dataclass
from typing import Protocol
import json
from agent.llm.prompt_builder import (
    LLMPrompt,
)


@dataclass(frozen=True)
class LLMResponse:
    provider: str
    model: str

    content: str

    rag_context_used: bool
    sources: tuple[str, ...]

    requires_human_approval: bool
    allows_direct_cluster_write: bool

    external_request_performed: bool
    performs_write: bool = False


class LLMClient(Protocol):
    def generate(
        self,
        prompt: LLMPrompt,
    ) -> LLMResponse:
        """
        Generate a model response from an LLMPrompt.
        """
        ...


class MockLLMClient:
    """
    Deterministic local LLM client used for tests
    and local pipeline validation.

    No external model or network request is performed.
    """

    provider = "mock"
    model = "kubepilot-mock-v1"

    def generate(
        self,
        prompt: LLMPrompt,
    ) -> LLMResponse:
        if prompt.performs_write:
            raise ValueError(
                "LLM prompt unexpectedly declares "
                "a write operation."
            )

        if prompt.allows_direct_cluster_write:
            raise ValueError(
                "Direct Kubernetes writes are not allowed."
            )

        if not prompt.requires_human_approval:
            raise ValueError(
                "LLM prompt must require human approval."
            )

        if not prompt.system_prompt.strip():
            raise ValueError(
                "LLM system prompt is required."
            )

        if not prompt.user_prompt.strip():
            raise ValueError(
                "LLM user prompt is required."
            )

        content = json.dumps(
            {
                "summary": (
                    "KubePilot mock analysis of the "
                    "supplied SRE or FinOps signal."
                ),
                "evidence": [
                    (
                        "The analysis uses the supplied "
                        "prompt and available RAG context."
                    ),
                    (
                        "No direct Kubernetes mutation "
                        "is permitted."
                    ),
                ],
                "recommendation": (
                    "Review the available evidence and "
                    "prepare any configuration change "
                    "through GitOps with human approval."
                ),
                "uncertainty": (
                    "This is a deterministic mock response "
                    "and does not represent a real model "
                    "inference."
                ),
                "requires_human_approval": True,
                "allows_direct_cluster_write": False,
            }
        )

        return LLMResponse(
            provider=self.provider,
            model=self.model,
            content=content,
            rag_context_used=(
                prompt.rag_context_used
            ),
            sources=prompt.sources,
            requires_human_approval=True,
            allows_direct_cluster_write=False,
            external_request_performed=False,
            performs_write=False,
        )
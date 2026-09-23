from dataclasses import dataclass

from agent.llm.bedrock_client import (
    BedrockRequest,
)
from agent.llm.prompt_builder import (
    LLMPrompt,
)


@dataclass(frozen=True)
class BedrockExecutionGatewayResult:
    allowed: bool
    reason: str

    ready_to_invoke: bool

    external_request_allowed: bool

    performs_write: bool = False


def validate_bedrock_execution(
    *,
    prompt: LLMPrompt,
    request: BedrockRequest,
    live_authorized: bool,
) -> BedrockExecutionGatewayResult:
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

    if request.performs_write:
        raise ValueError(
            "Bedrock request unexpectedly declares "
            "a write operation."
        )

    if request.dry_run:
        return BedrockExecutionGatewayResult(
            allowed=False,
            reason=(
                "Bedrock request is dry-run only."
            ),
            ready_to_invoke=False,
            external_request_allowed=False,
            performs_write=False,
        )

    if not live_authorized:
        return BedrockExecutionGatewayResult(
            allowed=False,
            reason=(
                "Live Bedrock invocation requires "
                "explicit authorization."
            ),
            ready_to_invoke=False,
            external_request_allowed=False,
            performs_write=False,
        )

    return BedrockExecutionGatewayResult(
        allowed=True,
        reason=(
            "Live Bedrock invocation explicitly "
            "authorized."
        ),
        ready_to_invoke=True,
        external_request_allowed=True,
        performs_write=False,
    )
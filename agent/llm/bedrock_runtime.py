from dataclasses import dataclass
from typing import Any, Protocol

from agent.llm.bedrock_client import (
    BedrockRequest,
)
from agent.llm.client import (
    LLMResponse,
)
from agent.llm.prompt_builder import (
    LLMPrompt,
)


class BedrockRuntimeClient(Protocol):
    def converse(
        self,
        **kwargs: Any,
    ) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class BedrockRuntimeResult:
    response: LLMResponse

    runtime_invoked: bool
    external_request_performed: bool

    input_tokens: int | None
    output_tokens: int | None

    stop_reason: str | None

    performs_write: bool = False


class BedrockRuntimeAdapter:
    """
    Adapter around an injected Bedrock Runtime client.

    The adapter itself does not create AWS credentials,
    sessions, or boto3 clients.

    Tests can inject a deterministic fake client.

    Real AWS wiring will be added separately.
    """

    def __init__(
        self,
        *,
        runtime_client: BedrockRuntimeClient,
        external_request_performed: bool = False,
    ) -> None:
        self._runtime_client = runtime_client
        self._external_request_performed = (
            external_request_performed
        )

    def invoke(
        self,
        *,
        prompt: LLMPrompt,
        request: BedrockRequest,
    ) -> BedrockRuntimeResult:
        self._validate(
            prompt=prompt,
            request=request,
        )

        runtime_response = (
            self._runtime_client.converse(
                modelId=request.model_id,
                system=[
                    {
                        "text": request.system_prompt,
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "text": request.user_prompt,
                            }
                        ],
                    }
                ],
                inferenceConfig={
                    "maxTokens": request.max_tokens,
                    "temperature": (
                        request.temperature
                    ),
                },
            )
        )

        content = self._extract_text(
            runtime_response
        )

        usage = runtime_response.get(
            "usage",
            {},
        )

        input_tokens = usage.get(
            "inputTokens"
        )

        output_tokens = usage.get(
            "outputTokens"
        )

        stop_reason = runtime_response.get(
            "stopReason"
        )

        response = LLMResponse(
            provider="aws-bedrock",
            model=request.model_id,
            content=content,
            rag_context_used=(
                prompt.rag_context_used
            ),
            sources=prompt.sources,
            requires_human_approval=True,
            allows_direct_cluster_write=False,
            external_request_performed=(
                self._external_request_performed
            ),
            performs_write=False,
        )

        return BedrockRuntimeResult(
            response=response,
            runtime_invoked=True,
            external_request_performed=(
                self._external_request_performed
            ),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            stop_reason=stop_reason,
            performs_write=False,
        )

    def _validate(
        self,
        *,
        prompt: LLMPrompt,
        request: BedrockRequest,
    ) -> None:
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

        if not request.model_id.strip():
            raise ValueError(
                "Bedrock model_id is required."
            )

        if not request.system_prompt.strip():
            raise ValueError(
                "Bedrock system prompt is required."
            )

        if not request.user_prompt.strip():
            raise ValueError(
                "Bedrock user prompt is required."
            )

        if request.max_tokens <= 0:
            raise ValueError(
                "Bedrock max_tokens must be "
                "greater than zero."
            )

        if (
            request.temperature < 0.0
            or request.temperature > 1.0
        ):
            raise ValueError(
                "Bedrock temperature must be "
                "between 0 and 1."
            )

    @staticmethod
    def _extract_text(
        response: dict[str, Any],
    ) -> str:
        try:
            content_blocks = (
                response["output"]
                ["message"]
                ["content"]
            )
        except (
            KeyError,
            TypeError,
        ) as exc:
            raise ValueError(
                "Bedrock response does not contain "
                "a valid output message."
            ) from exc

        texts = []

        for block in content_blocks:
            if not isinstance(
                block,
                dict,
            ):
                continue

            text = block.get(
                "text"
            )

            if isinstance(
                text,
                str,
            ) and text.strip():
                texts.append(
                    text.strip()
                )

        if not texts:
            raise ValueError(
                "Bedrock response contains no text."
            )

        return "\n".join(
            texts
        )
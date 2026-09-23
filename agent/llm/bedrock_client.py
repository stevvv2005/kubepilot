from dataclasses import dataclass

from agent.llm.client import (
    LLMResponse,
)
from agent.llm.prompt_builder import (
    LLMPrompt,
)


DEFAULT_BEDROCK_REGION = "eu-west-3"

DEFAULT_MAX_TOKENS = 1024

DEFAULT_TEMPERATURE = 0.2


@dataclass(frozen=True)
class BedrockRequest:
    region: str
    model_id: str

    system_prompt: str
    user_prompt: str

    max_tokens: int
    temperature: float

    dry_run: bool

    performs_write: bool = False


@dataclass(frozen=True)
class BedrockDryRunResult:
    request: BedrockRequest
    response: LLMResponse

    would_invoke_model: bool
    invoked_model: bool

    external_request_performed: bool

    performs_write: bool = False


class BedrockLLMClient:
    """
    Safe Bedrock client preparation layer.

    This version supports dry-run only.

    It validates the LLM prompt and builds the
    Bedrock request that would be sent later.

    No AWS network request is performed.
    """

    provider = "aws-bedrock"

    def __init__(
        self,
        *,
        model_id: str,
        region: str = DEFAULT_BEDROCK_REGION,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> None:
        normalized_model_id = model_id.strip()
        normalized_region = region.strip()

        if not normalized_model_id:
            raise ValueError(
                "Bedrock model_id is required."
            )

        if not normalized_region:
            raise ValueError(
                "Bedrock region is required."
            )

        if max_tokens <= 0:
            raise ValueError(
                "Bedrock max_tokens must be greater than zero."
            )

        if temperature < 0.0 or temperature > 1.0:
            raise ValueError(
                "Bedrock temperature must be between 0 and 1."
            )

        self.model_id = normalized_model_id
        self.region = normalized_region
        self.max_tokens = max_tokens
        self.temperature = temperature

    def _validate_prompt(
        self,
        prompt: LLMPrompt,
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

        if not prompt.system_prompt.strip():
            raise ValueError(
                "LLM system prompt is required."
            )

        if not prompt.user_prompt.strip():
            raise ValueError(
                "LLM user prompt is required."
            )

    def build_request(
        self,
        prompt: LLMPrompt,
        *,
        dry_run: bool = True,
    ) -> BedrockRequest:
        """
        Build a safe Bedrock request.

        Real execution is intentionally disabled
        in this implementation.
        """

        self._validate_prompt(
            prompt
        )

        if not dry_run:
            raise ValueError(
                "Real Bedrock invocation is disabled. "
                "Use dry_run=True."
            )

        return BedrockRequest(
            region=self.region,
            model_id=self.model_id,
            system_prompt=(
                prompt.system_prompt
            ),
            user_prompt=(
                prompt.user_prompt
            ),
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            dry_run=True,
            performs_write=False,
        )

    def generate(
        self,
        prompt: LLMPrompt,
        *,
        dry_run: bool = True,
    ) -> BedrockDryRunResult:
        """
        Prepare a Bedrock invocation in dry-run mode.

        No AWS API call is performed.
        """

        request = self.build_request(
            prompt,
            dry_run=dry_run,
        )

        content = (
            "Bedrock invocation prepared in dry-run mode. "
            "No AWS model request was performed."
        )

        response = LLMResponse(
            provider=self.provider,
            model=self.model_id,
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

        return BedrockDryRunResult(
            request=request,
            response=response,
            would_invoke_model=True,
            invoked_model=False,
            external_request_performed=False,
            performs_write=False,
        )
import os
from dataclasses import dataclass

from agent.llm.bedrock_aws_client import (
    BedrockAWSClientConfig,
    create_bedrock_runtime_adapter,
)
from agent.llm.bedrock_client import (
    BedrockLLMClient,
)
from agent.llm.bedrock_execution_gateway import (
    validate_bedrock_execution,
)
from agent.llm.client import (
    LLMResponse,
    MockLLMClient,
)
from agent.llm.prompt_builder import (
    LLMPrompt,
)


DEFAULT_PROVIDER = "mock"

DEFAULT_BEDROCK_MODEL_ID = (
    "eu.amazon.nova-micro-v1:0"
)

DEFAULT_BEDROCK_REGION = "eu-west-3"


@dataclass(frozen=True)
class LLMProviderSelection:
    provider: str
    live_authorized: bool

    model_id: str | None
    region: str | None

    external_request_allowed: bool

    performs_write: bool = False


def get_provider_selection() -> LLMProviderSelection:
    provider = os.getenv(
        "KUBEPILOT_LLM_PROVIDER",
        DEFAULT_PROVIDER,
    ).strip().lower()

    live_authorized = (
        os.getenv(
            "KUBEPILOT_BEDROCK_LIVE_AUTHORIZED",
            "",
        ).strip().lower()
        == "true"
    )

    if provider == "mock":
        return LLMProviderSelection(
            provider="mock",
            live_authorized=False,
            model_id=None,
            region=None,
            external_request_allowed=False,
            performs_write=False,
        )

    if provider == "bedrock":
        return LLMProviderSelection(
            provider="bedrock",
            live_authorized=live_authorized,
            model_id=DEFAULT_BEDROCK_MODEL_ID,
            region=DEFAULT_BEDROCK_REGION,
            external_request_allowed=(
                live_authorized
            ),
            performs_write=False,
        )

    raise ValueError(
        "Unsupported KubePilot LLM provider. "
        "Allowed providers: mock, bedrock."
    )


def generate_with_selected_provider(
    *,
    prompt: LLMPrompt,
    selection: LLMProviderSelection,
) -> LLMResponse:
    if selection.performs_write:
        raise ValueError(
            "LLM provider selection must not "
            "declare a write operation."
        )

    if selection.provider == "mock":
        return MockLLMClient().generate(
            prompt
        )

    if selection.provider != "bedrock":
        raise ValueError(
            "Unsupported LLM provider."
        )

    if not selection.live_authorized:
        raise ValueError(
            "Bedrock provider requires explicit "
            "live authorization."
        )

    if not selection.model_id:
        raise ValueError(
            "Bedrock model_id is required."
        )

    if not selection.region:
        raise ValueError(
            "Bedrock region is required."
        )

    bedrock_client = BedrockLLMClient(
        model_id=selection.model_id,
        region=selection.region,
        max_tokens=256,
        temperature=0.1,
    )

    request = bedrock_client.build_request(
        prompt,
        dry_run=False,
    )

    gateway = validate_bedrock_execution(
        prompt=prompt,
        request=request,
        live_authorized=(
            selection.live_authorized
        ),
    )

    adapter = create_bedrock_runtime_adapter(
        config=BedrockAWSClientConfig(
            region=selection.region,
        )
    )

    result = adapter.invoke(
        prompt=prompt,
        request=request,
        gateway=gateway,
    )

    return result.response
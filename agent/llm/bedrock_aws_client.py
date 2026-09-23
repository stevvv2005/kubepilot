from dataclasses import dataclass
from typing import Any, Callable

from agent.llm.bedrock_client import (
    DEFAULT_BEDROCK_REGION,
)
from agent.llm.bedrock_runtime import (
    BedrockRuntimeAdapter,
)


@dataclass(frozen=True)
class BedrockAWSClientConfig:
    region: str = DEFAULT_BEDROCK_REGION
    service_name: str = "bedrock-runtime"

    external_request_performed: bool = True

    performs_write: bool = False


def _validate_config(
    config: BedrockAWSClientConfig,
) -> None:
    if not config.region.strip():
        raise ValueError(
            "AWS Bedrock region is required."
        )

    if config.service_name != "bedrock-runtime":
        raise ValueError(
            "Only the bedrock-runtime service is allowed."
        )

    if config.performs_write:
        raise ValueError(
            "Bedrock AWS client config must not "
            "declare a write operation."
        )


def _default_boto3_client_factory(
    *,
    service_name: str,
    region_name: str,
) -> Any:
    """
    Create a boto3 client using the normal AWS
    credential provider chain.

    Credentials are never passed directly here.
    """

    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError(
            "boto3 is required for real AWS "
            "Bedrock runtime access."
        ) from exc

    return boto3.client(
        service_name,
        region_name=region_name,
    )


def create_bedrock_runtime_adapter(
    *,
    config: BedrockAWSClientConfig | None = None,
    client_factory: Callable[..., Any] | None = None,
) -> BedrockRuntimeAdapter:
    """
    Create a BedrockRuntimeAdapter using an AWS
    Bedrock Runtime client.

    The client factory is injectable so tests can
    run without AWS or network access.
    """

    resolved_config = (
        config
        if config is not None
        else BedrockAWSClientConfig()
    )

    _validate_config(
        resolved_config
    )

    factory = (
        client_factory
        if client_factory is not None
        else _default_boto3_client_factory
    )

    runtime_client = factory(
        service_name=resolved_config.service_name,
        region_name=resolved_config.region,
    )

    if runtime_client is None:
        raise ValueError(
            "AWS Bedrock runtime client factory "
            "returned no client."
        )

    return BedrockRuntimeAdapter(
        runtime_client=runtime_client,
        external_request_performed=(
            resolved_config
            .external_request_performed
        ),
    )
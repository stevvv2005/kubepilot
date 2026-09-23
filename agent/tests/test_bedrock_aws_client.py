import pytest

import agent.llm.bedrock_aws_client as aws_client_module
from agent.llm.bedrock_aws_client import (
    BedrockAWSClientConfig,
    create_bedrock_runtime_adapter,
)


class FakeRuntimeClient:
    def converse(
        self,
        **kwargs,
    ):
        return {}


def test_default_config():
    config = BedrockAWSClientConfig()

    assert config.region == "eu-west-3"

    assert (
        config.service_name
        == "bedrock-runtime"
    )

    assert (
        config.external_request_performed
        is True
    )

    assert config.performs_write is False


def test_create_adapter_with_injected_factory():
    captured = {}

    def fake_factory(
        *,
        service_name,
        region_name,
    ):
        captured["service_name"] = (
            service_name
        )

        captured["region_name"] = (
            region_name
        )

        return FakeRuntimeClient()

    adapter = create_bedrock_runtime_adapter(
        client_factory=fake_factory,
    )

    assert adapter is not None

    assert (
        captured["service_name"]
        == "bedrock-runtime"
    )

    assert (
        captured["region_name"]
        == "eu-west-3"
    )


def test_custom_region_is_supported():
    captured = {}

    def fake_factory(
        *,
        service_name,
        region_name,
    ):
        captured["region_name"] = (
            region_name
        )

        return FakeRuntimeClient()

    config = BedrockAWSClientConfig(
        region="eu-west-1",
    )

    create_bedrock_runtime_adapter(
        config=config,
        client_factory=fake_factory,
    )

    assert (
        captured["region_name"]
        == "eu-west-1"
    )


def test_empty_region_is_rejected():
    config = BedrockAWSClientConfig(
        region="   ",
    )

    with pytest.raises(
        ValueError,
        match="region is required",
    ):
        create_bedrock_runtime_adapter(
            config=config,
            client_factory=lambda **kwargs: (
                FakeRuntimeClient()
            ),
        )


def test_non_runtime_service_is_rejected():
    config = BedrockAWSClientConfig(
        service_name="bedrock",
    )

    with pytest.raises(
        ValueError,
        match=(
            "Only the bedrock-runtime "
            "service is allowed"
        ),
    ):
        create_bedrock_runtime_adapter(
            config=config,
            client_factory=lambda **kwargs: (
                FakeRuntimeClient()
            ),
        )


def test_write_declaring_config_is_rejected():
    config = BedrockAWSClientConfig(
        performs_write=True,
    )

    with pytest.raises(
        ValueError,
        match="must not declare",
    ):
        create_bedrock_runtime_adapter(
            config=config,
            client_factory=lambda **kwargs: (
                FakeRuntimeClient()
            ),
        )


def test_factory_returning_none_is_rejected():
    with pytest.raises(
        ValueError,
        match="returned no client",
    ):
        create_bedrock_runtime_adapter(
            client_factory=(
                lambda **kwargs: None
            ),
        )


def test_default_factory_uses_boto3(
    monkeypatch,
):
    captured = {}

    class FakeBoto3:
        @staticmethod
        def client(
            service_name,
            region_name,
        ):
            captured["service_name"] = (
                service_name
            )

            captured["region_name"] = (
                region_name
            )

            return FakeRuntimeClient()

    monkeypatch.setitem(
        __import__("sys").modules,
        "boto3",
        FakeBoto3,
    )

    runtime_client = (
        aws_client_module
        ._default_boto3_client_factory(
            service_name="bedrock-runtime",
            region_name="eu-west-3",
        )
    )

    assert runtime_client is not None

    assert (
        captured["service_name"]
        == "bedrock-runtime"
    )

    assert (
        captured["region_name"]
        == "eu-west-3"
    )
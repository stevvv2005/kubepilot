import pytest

from agent.llm.provider_selector import (
    get_provider_selection,
)


def test_default_provider_is_mock(
    monkeypatch,
):
    monkeypatch.delenv(
        "KUBEPILOT_LLM_PROVIDER",
        raising=False,
    )

    monkeypatch.delenv(
        "KUBEPILOT_BEDROCK_LIVE_AUTHORIZED",
        raising=False,
    )

    selection = get_provider_selection()

    assert selection.provider == "mock"
    assert selection.live_authorized is False

    assert (
        selection.external_request_allowed
        is False
    )

    assert selection.model_id is None
    assert selection.region is None

    assert selection.performs_write is False


def test_bedrock_without_authorization(
    monkeypatch,
):
    monkeypatch.setenv(
        "KUBEPILOT_LLM_PROVIDER",
        "bedrock",
    )

    monkeypatch.delenv(
        "KUBEPILOT_BEDROCK_LIVE_AUTHORIZED",
        raising=False,
    )

    selection = get_provider_selection()

    assert selection.provider == "bedrock"
    assert selection.live_authorized is False

    assert (
        selection.external_request_allowed
        is False
    )

    assert (
        selection.model_id
        == "eu.amazon.nova-micro-v1:0"
    )

    assert selection.region == "eu-west-3"


def test_bedrock_with_authorization(
    monkeypatch,
):
    monkeypatch.setenv(
        "KUBEPILOT_LLM_PROVIDER",
        "bedrock",
    )

    monkeypatch.setenv(
        "KUBEPILOT_BEDROCK_LIVE_AUTHORIZED",
        "true",
    )

    selection = get_provider_selection()

    assert selection.provider == "bedrock"
    assert selection.live_authorized is True

    assert (
        selection.external_request_allowed
        is True
    )


def test_unknown_provider_is_rejected(
    monkeypatch,
):
    monkeypatch.setenv(
        "KUBEPILOT_LLM_PROVIDER",
        "unknown",
    )

    with pytest.raises(
        ValueError,
        match="Unsupported KubePilot LLM provider",
    ):
        get_provider_selection()
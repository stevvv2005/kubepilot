from dataclasses import replace

import pytest

from agent.notifications.slack_payload import (
    build_finops_slack_payload,
    build_sre_slack_payload,
)
from agent.notifications.slack_sender import (
    send_slack_notification,
)


def _sre_payload():
    return build_sre_slack_payload(
        incident_type="OOMKilled",
        namespace="default",
        workload_name="checkoutservice",
        root_cause="Container exceeded memory limit.",
        recommendation=(
            "Review memory configuration through GitOps."
        ),
        confidence="high",
    )


def _finops_payload():
    return build_finops_slack_payload(
        namespace="default",
        workload_name="checkoutservice",
        current_monthly_cost_usd=2.47,
        estimated_monthly_savings_usd=0.62,
        current_cpu_request="100m",
        proposed_cpu_request="50m",
        current_memory_request="64Mi",
        proposed_memory_request="32Mi",
        confidence="medium",
    )


def test_sre_slack_sender_dry_run():
    result = send_slack_notification(
        _sre_payload(),
        destination="#kubepilot-alerts",
        dry_run=True,
    )

    assert result.notification_type == "sre"
    assert result.dry_run is True
    assert result.would_send is True
    assert result.sent is False
    assert result.destination == "#kubepilot-alerts"
    assert result.performs_write is False


def test_finops_slack_sender_dry_run():
    result = send_slack_notification(
        _finops_payload(),
        destination="#kubepilot-finops",
        dry_run=True,
    )

    assert result.notification_type == "finops"
    assert result.would_send is True
    assert result.sent is False
    assert result.performs_write is False


def test_real_slack_delivery_is_disabled():
    with pytest.raises(
        ValueError,
        match="Real Slack delivery is disabled",
    ):
        send_slack_notification(
            _sre_payload(),
            destination="#kubepilot-alerts",
            dry_run=False,
        )


def test_missing_destination_is_rejected():
    with pytest.raises(
        ValueError,
        match="Slack destination is required",
    ):
        send_slack_notification(
            _sre_payload(),
            destination="",
        )


def test_payload_declaring_write_is_rejected():
    payload = replace(
        _sre_payload(),
        performs_write=True,
    )

    with pytest.raises(
        ValueError,
        match="unexpectedly declares a write operation",
    ):
        send_slack_notification(
            payload,
            destination="#kubepilot-alerts",
        )


def test_missing_title_is_rejected():
    payload = replace(
        _sre_payload(),
        title="",
    )

    with pytest.raises(
        ValueError,
        match="Slack notification title is required",
    ):
        send_slack_notification(
            payload,
            destination="#kubepilot-alerts",
        )


def test_missing_notification_type_is_rejected():
    payload = replace(
        _sre_payload(),
        notification_type="",
    )

    with pytest.raises(
        ValueError,
        match="Slack notification type is required",
    ):
        send_slack_notification(
            payload,
            destination="#kubepilot-alerts",
        )
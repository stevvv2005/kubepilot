from agent.notifications.slack_payload import (
    build_finops_slack_payload,
    build_sre_slack_payload,
)


def test_build_sre_slack_payload():
    payload = build_sre_slack_payload(
        incident_type="OOMKilled",
        namespace="default",
        workload_name="checkoutservice",
        root_cause="Container exceeded memory limit.",
        recommendation=(
            "Review memory configuration through GitOps."
        ),
        confidence="high",
    )

    assert payload.notification_type == "sre"

    assert (
        payload.title
        == "KubePilot SRE Incident: OOMKilled"
    )

    assert payload.namespace == "default"

    assert (
        payload.workload_name
        == "checkoutservice"
    )

    assert payload.severity == "high"
    assert payload.status == "diagnosed"

    assert payload.requires_human_approval is True
    assert payload.dry_run is True
    assert payload.performs_write is False

    assert any(
        "OOMKilled" in detail
        for detail in payload.details
    )


def test_sre_medium_confidence_maps_to_medium_severity():
    payload = build_sre_slack_payload(
        incident_type="ReadinessProbeFailed",
        namespace="default",
        workload_name="frontend",
        root_cause="Readiness probe is failing.",
        recommendation="Review readiness configuration.",
        confidence="medium",
    )

    assert payload.severity == "medium"


def test_build_finops_slack_payload():
    payload = build_finops_slack_payload(
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

    assert payload.notification_type == "finops"

    assert (
        payload.title
        == (
            "KubePilot FinOps Recommendation: "
            "checkoutservice"
        )
    )

    assert payload.namespace == "default"
    assert payload.workload_name == "checkoutservice"

    assert payload.severity == "medium"
    assert payload.status == "recommendation"

    assert payload.requires_human_approval is True
    assert payload.dry_run is True
    assert payload.performs_write is False

    assert (
        "Current monthly cost: $2.47"
        in payload.details
    )

    assert (
        "Estimated monthly savings: $0.62"
        in payload.details
    )

    assert (
        "CPU request: 100m -> 50m"
        in payload.details
    )

    assert (
        "Memory request: 64Mi -> 32Mi"
        in payload.details
    )


def test_finops_payload_can_handle_missing_resource_values():
    payload = build_finops_slack_payload(
        namespace="default",
        workload_name="example",
        current_monthly_cost_usd=10.0,
        estimated_monthly_savings_usd=2.5,
        current_cpu_request=None,
        proposed_cpu_request=None,
        current_memory_request="64Mi",
        proposed_memory_request="32Mi",
        confidence="low",
    )

    assert (
        "CPU request: None -> None"
        in payload.details
    )

    assert payload.performs_write is False
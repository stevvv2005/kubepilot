from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SlackNotificationPayload:
    notification_type: str

    title: str
    summary: str

    namespace: Optional[str]
    workload_name: Optional[str]

    severity: str
    status: str

    details: tuple[str, ...]

    requires_human_approval: bool
    dry_run: bool

    performs_write: bool = False


def build_sre_slack_payload(
    *,
    incident_type: str,
    namespace: str,
    workload_name: str,
    root_cause: str,
    recommendation: str,
    confidence: str,
    requires_human_approval: bool = True,
    dry_run: bool = True,
) -> SlackNotificationPayload:
    """
    Build a Slack payload for an SRE incident.

    This function only prepares data.
    It does not send anything to Slack.
    """

    severity = (
        "high"
        if confidence == "high"
        else "medium"
    )

    return SlackNotificationPayload(
        notification_type="sre",
        title=f"KubePilot SRE Incident: {incident_type}",
        summary=root_cause,
        namespace=namespace,
        workload_name=workload_name,
        severity=severity,
        status="diagnosed",
        details=(
            f"Incident: {incident_type}",
            f"Root cause: {root_cause}",
            f"Recommendation: {recommendation}",
            f"Confidence: {confidence}",
        ),
        requires_human_approval=(
            requires_human_approval
        ),
        dry_run=dry_run,
        performs_write=False,
    )


def build_finops_slack_payload(
    *,
    namespace: str,
    workload_name: str,
    current_monthly_cost_usd: float,
    estimated_monthly_savings_usd: float,
    current_cpu_request: Optional[str],
    proposed_cpu_request: Optional[str],
    current_memory_request: Optional[str],
    proposed_memory_request: Optional[str],
    confidence: str,
    requires_human_approval: bool = True,
    dry_run: bool = True,
) -> SlackNotificationPayload:
    """
    Build a Slack payload for a FinOps rightsizing recommendation.

    This function only prepares data.
    It does not send anything to Slack.
    """

    return SlackNotificationPayload(
        notification_type="finops",
        title=(
            "KubePilot FinOps Recommendation: "
            f"{workload_name}"
        ),
        summary=(
            "Potential resource waste detected "
            "and a rightsizing proposal is available."
        ),
        namespace=namespace,
        workload_name=workload_name,
        severity="medium",
        status="recommendation",
        details=(
            (
                "Current monthly cost: "
                f"${current_monthly_cost_usd:.2f}"
            ),
            (
                "Estimated monthly savings: "
                f"${estimated_monthly_savings_usd:.2f}"
            ),
            (
                "CPU request: "
                f"{current_cpu_request} -> "
                f"{proposed_cpu_request}"
            ),
            (
                "Memory request: "
                f"{current_memory_request} -> "
                f"{proposed_memory_request}"
            ),
            f"Confidence: {confidence}",
        ),
        requires_human_approval=(
            requires_human_approval
        ),
        dry_run=dry_run,
        performs_write=False,
    )
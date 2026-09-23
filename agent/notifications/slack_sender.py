from dataclasses import dataclass

from agent.notifications.slack_payload import (
    SlackNotificationPayload,
)


@dataclass(frozen=True)
class SlackSendResult:
    notification_type: str
    title: str

    dry_run: bool

    would_send: bool
    sent: bool

    destination: str

    performs_write: bool = False


def send_slack_notification(
    payload: SlackNotificationPayload,
    *,
    destination: str,
    dry_run: bool = True,
) -> SlackSendResult:
    """
    Send a Slack notification in dry-run mode only.

    Real Slack delivery is intentionally disabled.
    """

    if not destination.strip():
        raise ValueError(
            "Slack destination is required."
        )

    if payload.performs_write:
        raise ValueError(
            "Slack payload unexpectedly declares "
            "a write operation."
        )

    if not payload.title.strip():
        raise ValueError(
            "Slack notification title is required."
        )

    if not payload.notification_type.strip():
        raise ValueError(
            "Slack notification type is required."
        )

    if not dry_run:
        raise ValueError(
            "Real Slack delivery is disabled. "
            "Use dry_run=True."
        )

    return SlackSendResult(
        notification_type=payload.notification_type,
        title=payload.title,
        dry_run=True,
        would_send=True,
        sent=False,
        destination=destination,
        performs_write=False,
    )
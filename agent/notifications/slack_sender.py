import json
import os
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from agent.notifications.slack_payload import (
    SlackNotificationPayload,
)


DEFAULT_SLACK_TIMEOUT_SECONDS = 5.0

SLACK_WEBHOOK_ENV_VAR = "SLACK_WEBHOOK_URL"

ALLOWED_SLACK_WEBHOOK_HOSTS = {
    "hooks.slack.com",
}


@dataclass(frozen=True)
class SlackSendResult:
    notification_type: str
    title: str

    dry_run: bool

    would_send: bool
    sent: bool

    destination: str

    external_request_performed: bool

    performs_write: bool = False


def _validate_payload(
    payload: SlackNotificationPayload,
) -> None:
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


def _validate_destination(
    destination: str,
) -> None:
    if not destination.strip():
        raise ValueError(
            "Slack destination is required."
        )


def _get_slack_webhook_url() -> str:
    webhook_url = os.getenv(
        SLACK_WEBHOOK_ENV_VAR,
        "",
    ).strip()

    if not webhook_url:
        raise ValueError(
            "SLACK_WEBHOOK_URL is required "
            "for real Slack delivery."
        )

    return webhook_url


def _validate_slack_webhook_url(
    webhook_url: str,
) -> None:
    parsed = urlparse(webhook_url)

    if parsed.scheme != "https":
        raise ValueError(
            "Slack webhook URL must use HTTPS."
        )

    if parsed.hostname not in ALLOWED_SLACK_WEBHOOK_HOSTS:
        raise ValueError(
            "Slack webhook URL host is not allowed."
        )

    if not parsed.path.startswith("/services/"):
        raise ValueError(
            "Slack webhook URL path is invalid."
        )

    path_parts = [
        part
        for part in parsed.path.split("/")
        if part
    ]

    if len(path_parts) < 4:
        raise ValueError(
            "Slack webhook URL path is incomplete."
        )

    if parsed.username or parsed.password:
        raise ValueError(
            "Slack webhook URL must not contain credentials."
        )

    if parsed.query or parsed.fragment:
        raise ValueError(
            "Slack webhook URL must not contain "
            "query parameters or fragments."
        )


def _build_slack_message(
    payload: SlackNotificationPayload,
    destination: str,
) -> str:
    details = "\n".join(
        f"• {detail}"
        for detail in payload.details
    )

    return (
        f"*{payload.title}*\n"
        f"{payload.summary}\n\n"
        f"*Type:* {payload.notification_type}\n"
        f"*Severity:* {payload.severity}\n"
        f"*Status:* {payload.status}\n"
        f"*Namespace:* {payload.namespace or 'N/A'}\n"
        f"*Workload:* {payload.workload_name or 'N/A'}\n"
        f"*Destination:* {destination}\n"
        f"*Human approval required:* "
        f"{payload.requires_human_approval}\n\n"
        f"{details}"
    )


def _post_slack_webhook(
    *,
    webhook_url: str,
    message: str,
    timeout_seconds: float,
    blocks: list[dict] | None = None,
) -> None:
    payload = {"text": message}
    if blocks is not None:
        payload["blocks"] = blocks
    body = json.dumps(payload).encode("utf-8")

    request = Request(
        webhook_url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "KubePilot/1.0",
        },
        method="POST",
    )

    try:
        with urlopen(
            request,
            timeout=timeout_seconds,
        ) as response:
            status_code = response.getcode()

            response_body = (
                response.read()
                .decode(
                    "utf-8",
                    errors="replace",
                )
                .strip()
            )

    except HTTPError as exc:
        raise RuntimeError(
            "Slack webhook returned HTTP "
            f"{exc.code}."
        ) from exc

    except URLError as exc:
        raise RuntimeError(
            "Unable to reach Slack webhook."
        ) from exc

    except TimeoutError as exc:
        raise RuntimeError(
            "Slack webhook request timed out."
        ) from exc

    if status_code < 200 or status_code >= 300:
        raise RuntimeError(
            "Slack webhook returned unexpected "
            f"HTTP status {status_code}."
        )

    if response_body.lower() != "ok":
        raise RuntimeError(
            "Slack webhook returned an unexpected response."
        )


def _build_slack_blocks(
    payload: SlackNotificationPayload,
    message: str,
) -> list[dict] | None:
    if not payload.remediation_id:
        return None

    evidence = "\n".join(
        f"• {item}" for item in payload.evidence
    ) or "• No additional evidence supplied"
    candidate = payload.candidate_value or "Manual review required"
    target = payload.target_manifest or "No trusted target resolved"

    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": message},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Evidence*\n{evidence}\n\n"
                    f"*Candidate value:* `{candidate}`\n"
                    f"*Trusted target:* `{target}`"
                ),
            },
        },
        {
            "type": "actions",
            "block_id": f"kubepilot_remediation_{payload.remediation_id}",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Approve"},
                    "style": "primary",
                    "action_id": "kubepilot_approve",
                    "value": payload.remediation_id,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Reject"},
                    "style": "danger",
                    "action_id": "kubepilot_reject",
                    "value": payload.remediation_id,
                },
            ],
        },
    ]


def send_slack_notification(
    payload: SlackNotificationPayload,
    *,
    destination: str,
    dry_run: bool = True,
    timeout_seconds: float = (
        DEFAULT_SLACK_TIMEOUT_SECONDS
    ),
) -> SlackSendResult:
    """
    Send a KubePilot Slack notification.

    Safety rules:

    - dry-run is enabled by default
    - dry-run performs no network request
    - webhook URL comes only from SLACK_WEBHOOK_URL
    - only Slack HTTPS webhook URLs are accepted
    - no Git or Kubernetes write is performed
    """

    _validate_destination(
        destination,
    )

    _validate_payload(
        payload,
    )

    if timeout_seconds <= 0:
        raise ValueError(
            "Slack timeout must be greater than zero."
        )

    if dry_run:
        return SlackSendResult(
            notification_type=(
                payload.notification_type
            ),
            title=payload.title,
            dry_run=True,
            would_send=True,
            sent=False,
            destination=destination,
            external_request_performed=False,
            performs_write=False,
        )

    webhook_url = _get_slack_webhook_url()

    _validate_slack_webhook_url(
        webhook_url,
    )

    message = _build_slack_message(
        payload=payload,
        destination=destination,
    )

    blocks = _build_slack_blocks(payload, message)

    if blocks is None:
        _post_slack_webhook(
            webhook_url=webhook_url,
            message=message,
            timeout_seconds=timeout_seconds,
        )
    else:
        _post_slack_webhook(
            webhook_url=webhook_url,
            message=message,
            timeout_seconds=timeout_seconds,
            blocks=blocks,
        )

    return SlackSendResult(
        notification_type=(
            payload.notification_type
        ),
        title=payload.title,
        dry_run=False,
        would_send=True,
        sent=True,
        destination=destination,
        external_request_performed=True,
        performs_write=False,
    )

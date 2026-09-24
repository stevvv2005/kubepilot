import hashlib
import hmac
import time


SLACK_SIGNING_SECRET_ENV_VAR = "SLACK_SIGNING_SECRET"
SLACK_SIGNATURE_VERSION = "v0"
SLACK_REQUEST_TOLERANCE_SECONDS = 300


class SlackSignatureError(ValueError):
    pass


def verify_slack_signature(
    *,
    raw_body: bytes,
    signature: str | None,
    timestamp: str | None,
    signing_secret: str,
    now: int | None = None,
    tolerance_seconds: int = SLACK_REQUEST_TOLERANCE_SECONDS,
) -> None:
    """Verify a Slack request before its body is parsed."""

    if not signature:
        raise SlackSignatureError("Missing Slack signature.")

    if not timestamp:
        raise SlackSignatureError("Missing Slack request timestamp.")

    if not signing_secret:
        raise SlackSignatureError("Slack signing secret is not configured.")

    try:
        request_timestamp = int(timestamp)
    except (TypeError, ValueError) as exc:
        raise SlackSignatureError(
            "Malformed Slack request timestamp."
        ) from exc

    current_time = int(time.time()) if now is None else now

    if abs(current_time - request_timestamp) > tolerance_seconds:
        raise SlackSignatureError("Stale Slack request timestamp.")

    try:
        body_text = raw_body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SlackSignatureError("Slack request body is not UTF-8.") from exc

    base_string = (
        f"{SLACK_SIGNATURE_VERSION}:{timestamp}:{body_text}"
    ).encode("utf-8")
    digest = hmac.new(
        signing_secret.encode("utf-8"),
        base_string,
        hashlib.sha256,
    ).hexdigest()
    expected_signature = f"{SLACK_SIGNATURE_VERSION}={digest}"

    if not hmac.compare_digest(expected_signature, signature):
        raise SlackSignatureError("Invalid Slack signature.")

import hashlib
import hmac

import pytest

from agent.notifications.slack_signature import (
    SlackSignatureError,
    verify_slack_signature,
)


SECRET = "test-signing-secret"
TIMESTAMP = 1_700_000_000
BODY = b"payload=%7B%22type%22%3A%22block_actions%22%7D"


def _signature(body: bytes = BODY, timestamp: int = TIMESTAMP) -> str:
    base = f"v0:{timestamp}:".encode() + body
    digest = hmac.new(SECRET.encode(), base, hashlib.sha256).hexdigest()
    return f"v0={digest}"


def test_valid_slack_signature():
    verify_slack_signature(
        raw_body=BODY,
        signature=_signature(),
        timestamp=str(TIMESTAMP),
        signing_secret=SECRET,
        now=TIMESTAMP,
    )


@pytest.mark.parametrize(
    ("signature", "timestamp", "message"),
    [
        ("v0=invalid", str(TIMESTAMP), "Invalid Slack signature"),
        (None, str(TIMESTAMP), "Missing Slack signature"),
        (_signature(), None, "Missing Slack request timestamp"),
    ],
)
def test_invalid_or_missing_slack_signature_headers(
    signature,
    timestamp,
    message,
):
    with pytest.raises(SlackSignatureError, match=message):
        verify_slack_signature(
            raw_body=BODY,
            signature=signature,
            timestamp=timestamp,
            signing_secret=SECRET,
            now=TIMESTAMP,
        )


def test_stale_slack_timestamp_is_rejected():
    with pytest.raises(SlackSignatureError, match="Stale"):
        verify_slack_signature(
            raw_body=BODY,
            signature=_signature(),
            timestamp=str(TIMESTAMP),
            signing_secret=SECRET,
            now=TIMESTAMP + 301,
        )

from dataclasses import dataclass

from agent.sre_agent.pr_payload import PullRequestPayload


@dataclass(frozen=True)
class GitHubPRGatewayResult:
    allowed: bool
    reason: str
    ready_to_send: bool
    performs_write: bool = False


def validate_pr_payload_for_github(
    payload: PullRequestPayload,
) -> GitHubPRGatewayResult:
    """
    Validate whether a Pull Request payload may proceed
    to the future GitHub integration layer.

    This function performs no GitHub write.
    """

    if not payload.ready_to_create:
        return GitHubPRGatewayResult(
            allowed=False,
            reason="Pull Request payload is not approved for creation.",
            ready_to_send=False,
        )

    if payload.approved_value is None:
        return GitHubPRGatewayResult(
            allowed=False,
            reason="An explicitly approved value is required.",
            ready_to_send=False,
        )

    if payload.writes_git:
        return GitHubPRGatewayResult(
            allowed=False,
            reason="Unexpected Git write flag detected.",
            ready_to_send=False,
        )

    if payload.creates_pr:
        return GitHubPRGatewayResult(
            allowed=False,
            reason="Unexpected Pull Request creation flag detected.",
            ready_to_send=False,
        )

    return GitHubPRGatewayResult(
        allowed=True,
        reason="Payload passed all GitHub PR safety checks.",
        ready_to_send=True,
        performs_write=False,
    )

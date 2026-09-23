from dataclasses import dataclass

from agent.sre_agent.git_commit_dry_run import GitCommitDryRun
from agent.sre_agent.github_pr import GitHubPRGatewayResult
from agent.sre_agent.pr_payload import PullRequestPayload


@dataclass(frozen=True)
class GitExecutionGatewayResult:
    allowed: bool
    reason: str
    ready_to_execute: bool
    performs_write: bool = False


def validate_git_execution(
    commit_plan: GitCommitDryRun,
    pr_payload: PullRequestPayload,
    github_gateway: GitHubPRGatewayResult,
) -> GitExecutionGatewayResult:
    """
    Validate whether a Git execution may proceed to a future executor.

    This function performs no file write, no Git command,
    and no GitHub operation.
    """

    if not commit_plan.ready_to_commit:
        return GitExecutionGatewayResult(
            allowed=False,
            reason="Git commit plan is not ready.",
            ready_to_execute=False,
        )

    if not pr_payload.ready_to_create:
        return GitExecutionGatewayResult(
            allowed=False,
            reason="Pull Request payload is not ready.",
            ready_to_execute=False,
        )

    if not github_gateway.allowed:
        return GitExecutionGatewayResult(
            allowed=False,
            reason="GitHub PR safety gateway blocked execution.",
            ready_to_execute=False,
        )

    if not github_gateway.ready_to_send:
        return GitExecutionGatewayResult(
            allowed=False,
            reason="GitHub PR request is not ready to send.",
            ready_to_execute=False,
        )

    if commit_plan.performs_write:
        return GitExecutionGatewayResult(
            allowed=False,
            reason="Unexpected write flag detected in commit plan.",
            ready_to_execute=False,
        )

    if commit_plan.writes_file:
        return GitExecutionGatewayResult(
            allowed=False,
            reason="Unexpected file write flag detected.",
            ready_to_execute=False,
        )

    if commit_plan.writes_git:
        return GitExecutionGatewayResult(
            allowed=False,
            reason="Unexpected Git write flag detected.",
            ready_to_execute=False,
        )

    if pr_payload.writes_git:
        return GitExecutionGatewayResult(
            allowed=False,
            reason="Unexpected PR payload Git write flag detected.",
            ready_to_execute=False,
        )

    if pr_payload.creates_pr:
        return GitExecutionGatewayResult(
            allowed=False,
            reason="Unexpected PR creation flag detected.",
            ready_to_execute=False,
        )

    return GitExecutionGatewayResult(
        allowed=True,
        reason="Git execution passed all safety checks.",
        ready_to_execute=True,
        performs_write=False,
    )

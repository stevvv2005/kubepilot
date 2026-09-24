from dataclasses import dataclass

from agent.finops_agent.git_execution_request import (
    FinOpsGitExecutionRequest,
)


@dataclass(frozen=True)
class GitHubExecutionGatewayResult:
    allowed: bool
    reason: str
    ready_to_execute: bool
    performs_cluster_write: bool = False


def validate_github_execution(
    *,
    request: FinOpsGitExecutionRequest,
    live_authorized: bool,
) -> GitHubExecutionGatewayResult:
    if not live_authorized:
        return GitHubExecutionGatewayResult(
            allowed=False,
            reason=(
                "GitHub live execution requires "
                "explicit authorization."
            ),
            ready_to_execute=False,
            performs_cluster_write=False,
        )

    if not request.authorized:
        return GitHubExecutionGatewayResult(
            allowed=False,
            reason=(
                "FinOps Git execution request "
                "is not authorized."
            ),
            ready_to_execute=False,
            performs_cluster_write=False,
        )

    if request.performs_write:
        return GitHubExecutionGatewayResult(
            allowed=False,
            reason=(
                "FinOps request unexpectedly "
                "declares a direct write."
            ),
            ready_to_execute=False,
            performs_cluster_write=False,
        )

    if request.head_branch == request.base_branch:
        return GitHubExecutionGatewayResult(
            allowed=False,
            reason=(
                "Head branch must differ "
                "from base branch."
            ),
            ready_to_execute=False,
            performs_cluster_write=False,
        )

    if not request.head_branch.startswith(
        "fix/finops-"
    ):
        return GitHubExecutionGatewayResult(
            allowed=False,
            reason=(
                "Head branch is outside "
                "the FinOps policy."
            ),
            ready_to_execute=False,
            performs_cluster_write=False,
        )

    return GitHubExecutionGatewayResult(
        allowed=True,
        reason=(
            "GitHub execution passed "
            "all safety checks."
        ),
        ready_to_execute=True,
        performs_cluster_write=False,
    )
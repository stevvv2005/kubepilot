from dataclasses import dataclass
import re

from agent.sre_agent.git_execution_request import GitExecutionRequest
from agent.sre_agent.target_file_resolver import is_allowlisted_target_file


ALLOWED_SRE_REPOSITORY = "stevvv2005/kubepilot"
ALLOWED_SRE_BASE_BRANCH = "main"
SRE_FIX_BRANCH_PREFIX = "fix/sre-"
_SRE_FIX_BRANCH_PATTERN = re.compile(
    r"^fix/sre-[a-z0-9]+(?:[._-][a-z0-9]+)*$"
)


@dataclass(frozen=True)
class SREGitHubExecutionGatewayResult:
    allowed: bool
    reason: str
    ready_to_execute: bool
    performs_cluster_write: bool = False


def validate_sre_github_execution(
    *,
    request: GitExecutionRequest,
    live_authorized: bool,
) -> SREGitHubExecutionGatewayResult:
    """
    Validate whether an SRE GitHub PR execution may proceed.

    This function performs no file, GitHub, or Kubernetes write.
    """

    if not live_authorized:
        return SREGitHubExecutionGatewayResult(
            allowed=False,
            reason=(
                "GitHub live execution requires "
                "explicit authorization."
            ),
            ready_to_execute=False,
        )

    if not request.authorized:
        return SREGitHubExecutionGatewayResult(
            allowed=False,
            reason="SRE Git execution request is not authorized.",
            ready_to_execute=False,
        )

    if request.performs_write:
        return SREGitHubExecutionGatewayResult(
            allowed=False,
            reason=(
                "SRE request unexpectedly declares "
                "a direct write."
            ),
            ready_to_execute=False,
        )

    if request.repository != ALLOWED_SRE_REPOSITORY:
        return SREGitHubExecutionGatewayResult(
            allowed=False,
            reason="Repository is outside the SRE live execution policy.",
            ready_to_execute=False,
        )

    if request.base_branch != ALLOWED_SRE_BASE_BRANCH:
        return SREGitHubExecutionGatewayResult(
            allowed=False,
            reason="Base branch is outside the SRE live execution policy.",
            ready_to_execute=False,
        )

    if request.head_branch == request.base_branch:
        return SREGitHubExecutionGatewayResult(
            allowed=False,
            reason="Head branch must differ from base branch.",
            ready_to_execute=False,
        )

    if (
        len(request.head_branch) > 100
        or request.head_branch.endswith(".lock")
        or _SRE_FIX_BRANCH_PATTERN.fullmatch(
            request.head_branch
        )
        is None
    ):
        return SREGitHubExecutionGatewayResult(
            allowed=False,
            reason="Head branch is outside the SRE branch policy.",
            ready_to_execute=False,
        )

    if not is_allowlisted_target_file(request.target_file):
        return SREGitHubExecutionGatewayResult(
            allowed=False,
            reason="Target file is outside the trusted SRE allowlist.",
            ready_to_execute=False,
        )

    if not request.rendered_yaml.strip():
        return SREGitHubExecutionGatewayResult(
            allowed=False,
            reason="Rendered YAML is required.",
            ready_to_execute=False,
        )

    if not request.create_branch:
        return SREGitHubExecutionGatewayResult(
            allowed=False,
            reason="GitHub execution requires branch creation.",
            ready_to_execute=False,
        )

    if not request.write_file:
        return SREGitHubExecutionGatewayResult(
            allowed=False,
            reason="GitHub execution requires file update.",
            ready_to_execute=False,
        )

    if not request.create_commit:
        return SREGitHubExecutionGatewayResult(
            allowed=False,
            reason="GitHub execution requires commit creation.",
            ready_to_execute=False,
        )

    if not request.push_branch:
        return SREGitHubExecutionGatewayResult(
            allowed=False,
            reason="GitHub execution requires branch publication.",
            ready_to_execute=False,
        )

    if not request.create_pr:
        return SREGitHubExecutionGatewayResult(
            allowed=False,
            reason="GitHub execution requires PR creation.",
            ready_to_execute=False,
        )

    return SREGitHubExecutionGatewayResult(
        allowed=True,
        reason="SRE GitHub execution passed all safety checks.",
        ready_to_execute=True,
        performs_cluster_write=False,
    )

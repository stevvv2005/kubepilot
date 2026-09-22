from dataclasses import dataclass
from typing import Optional

from agent.sre_agent.github_pr import GitHubPRGatewayResult
from agent.sre_agent.pr_payload import PullRequestPayload


@dataclass(frozen=True)
class GitHubPullRequestRequest:
    repository: str
    base_branch: str
    head_branch: str
    title: str
    body: str
    target_file: Optional[str]
    approved_value: Optional[str]
    ready_to_send: bool
    performs_write: bool = False


def build_github_pr_request(
    repository: str,
    base_branch: str,
    payload: PullRequestPayload,
    gateway: GitHubPRGatewayResult,
) -> GitHubPullRequestRequest:
    """
    Build a GitHub-ready Pull Request request.

    This function only prepares request data.
    It never calls GitHub and performs no write.
    """

    if not gateway.allowed or not gateway.ready_to_send:
        return GitHubPullRequestRequest(
            repository=repository,
            base_branch=base_branch,
            head_branch=payload.branch_name,
            title=payload.title,
            body=payload.pr_body,
            target_file=payload.target_file,
            approved_value=payload.approved_value,
            ready_to_send=False,
        )

    return GitHubPullRequestRequest(
        repository=repository,
        base_branch=base_branch,
        head_branch=payload.branch_name,
        title=payload.title,
        body=payload.pr_body,
        target_file=payload.target_file,
        approved_value=payload.approved_value,
        ready_to_send=True,
        performs_write=False,
    )

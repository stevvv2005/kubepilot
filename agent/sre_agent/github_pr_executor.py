from dataclasses import dataclass
from typing import Protocol

from agent.sre_agent.git_execution_request import GitExecutionRequest
from agent.sre_agent.github_execution_gateway import (
    validate_sre_github_execution,
)


@dataclass(frozen=True)
class SREGitHubPRExecutionResult:
    repository: str
    base_branch: str
    head_branch: str

    target_file: str
    commit_sha: str
    pr_number: int
    pr_url: str

    executed: bool
    performs_cluster_write: bool = False


class SREGitHubRepositoryClient(Protocol):
    def get_branch_sha(
        self,
        *,
        repository: str,
        branch: str,
    ) -> str:
        ...

    def create_branch(
        self,
        *,
        repository: str,
        branch: str,
        source_sha: str,
    ) -> None:
        ...

    def update_file(
        self,
        *,
        repository: str,
        branch: str,
        path: str,
        content: str,
        message: str,
    ) -> str:
        ...

    def create_pull_request(
        self,
        *,
        repository: str,
        base_branch: str,
        head_branch: str,
        title: str,
        body: str,
    ) -> tuple[int, str]:
        ...


def execute_sre_github_pr_request(
    *,
    request: GitExecutionRequest,
    client: SREGitHubRepositoryClient,
    live_authorized: bool,
) -> SREGitHubPRExecutionResult:
    """
    Execute an approved SRE GitOps remediation through GitHub.

    This function may write to GitHub only. It never writes directly
    to Kubernetes and never merges a Pull Request.
    """

    gateway = validate_sre_github_execution(
        request=request,
        live_authorized=live_authorized,
    )

    if not gateway.allowed:
        raise ValueError(gateway.reason)

    if not gateway.ready_to_execute:
        raise ValueError("SRE GitHub execution is not ready.")

    if gateway.performs_cluster_write:
        raise ValueError(
            "SRE GitHub execution must not perform cluster writes."
        )

    base_sha = client.get_branch_sha(
        repository=request.repository,
        branch=request.base_branch,
    )

    client.create_branch(
        repository=request.repository,
        branch=request.head_branch,
        source_sha=base_sha,
    )

    commit_sha = client.update_file(
        repository=request.repository,
        branch=request.head_branch,
        path=request.target_file,
        content=request.rendered_yaml,
        message=request.commit_message,
    )

    pr_number, pr_url = client.create_pull_request(
        repository=request.repository,
        base_branch=request.base_branch,
        head_branch=request.head_branch,
        title=request.pr_title,
        body=request.pr_body,
    )

    return SREGitHubPRExecutionResult(
        repository=request.repository,
        base_branch=request.base_branch,
        head_branch=request.head_branch,
        target_file=request.target_file,
        commit_sha=commit_sha,
        pr_number=pr_number,
        pr_url=pr_url,
        executed=True,
        performs_cluster_write=False,
    )

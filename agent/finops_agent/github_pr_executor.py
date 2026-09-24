from dataclasses import dataclass
from typing import Protocol

from agent.finops_agent.git_execution_request import (
    FinOpsGitExecutionRequest,
)


@dataclass(frozen=True)
class GitHubPRExecutionResult:
    repository: str
    base_branch: str
    head_branch: str

    target_file: str
    commit_sha: str
    pr_number: int
    pr_url: str

    executed: bool
    performs_cluster_write: bool = False


class GitHubRepositoryClient(Protocol):
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


def execute_github_pr_request(
    *,
    request: FinOpsGitExecutionRequest,
    client: GitHubRepositoryClient,
    live_authorized: bool,
) -> GitHubPRExecutionResult:
    """
    Execute an approved GitOps change through GitHub.

    This function may write to GitHub only.
    It never writes directly to Kubernetes.
    """

    if not live_authorized:
        raise ValueError(
            "GitHub live execution requires explicit authorization."
        )

    if not request.authorized:
        raise ValueError(
            "FinOps Git execution request is not authorized."
        )

    if request.performs_write:
        raise ValueError(
            "FinOps Git execution request unexpectedly "
            "declares a direct write operation."
        )

    if request.head_branch == request.base_branch:
        raise ValueError(
            "Head branch must differ from base branch."
        )

    if not request.head_branch.startswith(
        "fix/finops-"
    ):
        raise ValueError(
            "Head branch is outside the FinOps branch policy."
        )

    if not request.repository.strip():
        raise ValueError(
            "Repository is required."
        )

    if not request.target_file.strip():
        raise ValueError(
            "Target file is required."
        )

    if not request.rendered_yaml.strip():
        raise ValueError(
            "Rendered YAML is required."
        )

    if not request.create_branch:
        raise ValueError(
            "GitHub execution requires branch creation."
        )

    if not request.write_file:
        raise ValueError(
            "GitHub execution requires file update."
        )

    if not request.create_commit:
        raise ValueError(
            "GitHub execution requires commit creation."
        )

    if not request.push_branch:
        raise ValueError(
            "GitHub execution requires branch publication."
        )

    if not request.create_pr:
        raise ValueError(
            "GitHub execution requires PR creation."
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

    return GitHubPRExecutionResult(
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
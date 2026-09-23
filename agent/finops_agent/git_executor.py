from dataclasses import dataclass

from agent.finops_agent.git_execution_request import (
    FinOpsGitExecutionRequest,
)


@dataclass(frozen=True)
class FinOpsGitExecutionResult:
    repository: str
    base_branch: str
    head_branch: str

    target_file: str
    commit_message: str

    dry_run: bool

    would_create_branch: bool
    would_write_file: bool
    would_create_commit: bool
    would_push_branch: bool
    would_create_pr: bool

    executed: bool

    performs_write: bool = False


def execute_finops_git_request(
    request: FinOpsGitExecutionRequest,
    dry_run: bool = True,
) -> FinOpsGitExecutionResult:
    """
    Execute a FinOps Git request in dry-run mode only.

    Real Git execution is intentionally disabled.

    No file, Git, Kubernetes, or cloud write is performed.
    """

    if not request.authorized:
        raise ValueError(
            "FinOps Git execution request is not authorized."
        )

    if request.performs_write:
        raise ValueError(
            "FinOps Git execution request unexpectedly "
            "declares a write operation."
        )

    if not dry_run:
        raise ValueError(
            "Real FinOps Git execution is disabled. "
            "Use dry_run=True."
        )

    if not request.repository.strip():
        raise ValueError(
            "Repository is required."
        )

    if not request.base_branch.strip():
        raise ValueError(
            "Base branch is required."
        )

    if not request.head_branch.strip():
        raise ValueError(
            "Head branch is required."
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

    if not request.target_file.strip():
        raise ValueError(
            "Target file is required."
        )

    if not request.commit_message.strip():
        raise ValueError(
            "Commit message is required."
        )

    if not request.rendered_yaml.strip():
        raise ValueError(
            "Rendered YAML is required."
        )

    return FinOpsGitExecutionResult(
        repository=request.repository,
        base_branch=request.base_branch,
        head_branch=request.head_branch,
        target_file=request.target_file,
        commit_message=request.commit_message,
        dry_run=True,
        would_create_branch=request.create_branch,
        would_write_file=request.write_file,
        would_create_commit=request.create_commit,
        would_push_branch=request.push_branch,
        would_create_pr=request.create_pr,
        executed=False,
        performs_write=False,
    )
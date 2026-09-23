from dataclasses import dataclass

from agent.sre_agent.git_execution_request import GitExecutionRequest


@dataclass(frozen=True)
class GitExecutionResult:
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


def execute_git_request(
    request: GitExecutionRequest,
    dry_run: bool = True,
) -> GitExecutionResult:
    """
    Execute a Git execution request in dry-run mode.

    Real Git/file/GitHub execution is intentionally disabled
    in this version.

    No file, Git, GitHub, or Kubernetes write is performed.
    """

    if not request.authorized:
        raise ValueError(
            "Git execution request is not authorized."
        )

    if request.performs_write:
        raise ValueError(
            "Unexpected write flag detected in execution request."
        )

    if not dry_run:
        raise ValueError(
            "Real Git execution is disabled. Use dry_run=True."
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

    return GitExecutionResult(
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

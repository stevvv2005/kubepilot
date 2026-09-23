from dataclasses import dataclass

from agent.sre_agent.git_commit_dry_run import GitCommitDryRun
from agent.sre_agent.git_execution_gateway import (
    GitExecutionGatewayResult,
)
from agent.sre_agent.github_request import (
    GitHubPullRequestRequest,
)


@dataclass(frozen=True)
class GitExecutionRequest:
    repository: str
    base_branch: str
    head_branch: str

    target_file: str
    commit_message: str
    rendered_yaml: str

    pr_title: str
    pr_body: str

    create_branch: bool
    write_file: bool
    create_commit: bool
    push_branch: bool
    create_pr: bool

    authorized: bool
    performs_write: bool = False


def build_git_execution_request(
    commit_plan: GitCommitDryRun,
    execution_gateway: GitExecutionGatewayResult,
    github_request: GitHubPullRequestRequest,
) -> GitExecutionRequest:
    """
    Build the final request for a future Git executor.

    The request describes the operations that would be allowed,
    but this function does not execute any Git, GitHub, file,
    or Kubernetes write.
    """

    if not execution_gateway.allowed:
        raise ValueError(
            "Git execution gateway did not authorize execution."
        )

    if not execution_gateway.ready_to_execute:
        raise ValueError(
            "Git execution gateway is not ready to execute."
        )

    if execution_gateway.performs_write:
        raise ValueError(
            "Unexpected write flag detected in execution gateway."
        )

    if not commit_plan.ready_to_commit:
        raise ValueError(
            "Git commit plan is not ready."
        )

    if not github_request.ready_to_send:
        raise ValueError(
            "GitHub Pull Request request is not ready."
        )

    if commit_plan.target_file != github_request.target_file:
        raise ValueError(
            "Commit plan target file does not match GitHub request."
        )

    if commit_plan.branch_name != github_request.head_branch:
        raise ValueError(
            "Commit branch does not match GitHub head branch."
        )

    if not github_request.repository.strip():
        raise ValueError(
            "Repository is required."
        )

    if not github_request.base_branch.strip():
        raise ValueError(
            "Base branch is required."
        )

    if not github_request.head_branch.strip():
        raise ValueError(
            "Head branch is required."
        )

    if not commit_plan.commit_message.strip():
        raise ValueError(
            "Commit message is required."
        )

    if not commit_plan.rendered_yaml.strip():
        raise ValueError(
            "Rendered YAML is required."
        )

    return GitExecutionRequest(
        repository=github_request.repository,
        base_branch=github_request.base_branch,
        head_branch=github_request.head_branch,

        target_file=commit_plan.target_file,
        commit_message=commit_plan.commit_message,
        rendered_yaml=commit_plan.rendered_yaml,

        pr_title=github_request.title,
        pr_body=github_request.body,

        create_branch=True,
        write_file=True,
        create_commit=True,
        push_branch=True,
        create_pr=True,

        authorized=True,
        performs_write=False,
    )

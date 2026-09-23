from dataclasses import dataclass
from pathlib import PurePosixPath

from agent.finops_agent.git_commit_dry_run import (
    FinOpsGitCommitDryRun,
)
from agent.finops_agent.git_execution_gateway import (
    FinOpsGitExecutionGatewayResult,
)


@dataclass(frozen=True)
class FinOpsGitExecutionRequest:
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


def _is_safe_target_file(
    target_file: str,
) -> bool:
    """
    Validate that the target is a safe repository-relative path.
    """

    if not target_file.strip():
        return False

    path = PurePosixPath(
        target_file,
    )

    if path.is_absolute():
        return False

    if ".." in path.parts:
        return False

    return True


def _build_pr_title(
    commit_plan: FinOpsGitCommitDryRun,
) -> str:
    return commit_plan.commit_message


def _build_pr_body(
    commit_plan: FinOpsGitCommitDryRun,
) -> str:
    return (
        "## KubePilot FinOps Rightsizing\n\n"
        "This Pull Request contains a human-approved "
        "FinOps rightsizing change.\n\n"
        f"Target file: `{commit_plan.target_file}`\n\n"
        "The change was prepared through the KubePilot "
        "FinOps safety pipeline.\n\n"
        "- Human approval required before rendering\n"
        "- No direct Kubernetes mutation\n"
        "- No automatic apply\n"
        "- GitOps remains the deployment source of truth\n"
    )


def build_finops_git_execution_request(
    commit_plan: FinOpsGitCommitDryRun,
    gateway: FinOpsGitExecutionGatewayResult,
    repository: str,
    base_branch: str = "main",
) -> FinOpsGitExecutionRequest:
    """
    Build a description of future Git operations.

    This function performs no file or Git write.
    """

    if not gateway.allowed:
        raise ValueError(
            "FinOps Git execution gateway did not allow execution."
        )

    if not gateway.ready_to_execute:
        raise ValueError(
            "FinOps Git execution gateway is not ready."
        )

    if gateway.performs_write:
        raise ValueError(
            "FinOps Git execution gateway must not perform writes."
        )

    if not commit_plan.ready_to_commit:
        raise ValueError(
            "FinOps commit plan is not ready."
        )

    if (
        commit_plan.performs_write
        or commit_plan.writes_file
        or commit_plan.writes_git
    ):
        raise ValueError(
            "FinOps commit plan contains unexpected write flags."
        )

    repository = repository.strip()

    if not repository:
        raise ValueError(
            "Repository is required."
        )

    base_branch = base_branch.strip()

    if not base_branch:
        raise ValueError(
            "Base branch is required."
        )

    if not commit_plan.branch_name.strip():
        raise ValueError(
            "Head branch is required."
        )

    if (
        commit_plan.branch_name
        == base_branch
    ):
        raise ValueError(
            "Head branch must differ from base branch."
        )

    if not commit_plan.branch_name.startswith(
        "fix/finops-"
    ):
        raise ValueError(
            "Head branch is outside the FinOps branch policy."
        )

    if not _is_safe_target_file(
        commit_plan.target_file
    ):
        raise ValueError(
            "FinOps target file is not a safe repository-relative path."
        )

    if not commit_plan.commit_message.strip():
        raise ValueError(
            "Commit message is required."
        )

    if not commit_plan.rendered_yaml.strip():
        raise ValueError(
            "Rendered YAML is required."
        )

    return FinOpsGitExecutionRequest(
        repository=repository,
        base_branch=base_branch,
        head_branch=commit_plan.branch_name,
        target_file=commit_plan.target_file,
        commit_message=commit_plan.commit_message,
        rendered_yaml=commit_plan.rendered_yaml,
        pr_title=_build_pr_title(
            commit_plan,
        ),
        pr_body=_build_pr_body(
            commit_plan,
        ),
        create_branch=True,
        write_file=True,
        create_commit=True,
        push_branch=True,
        create_pr=True,
        authorized=True,
        performs_write=False,
    )
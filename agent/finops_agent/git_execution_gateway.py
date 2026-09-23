from dataclasses import dataclass

from agent.finops_agent.git_commit_dry_run import (
    FinOpsGitCommitDryRun,
)


@dataclass(frozen=True)
class FinOpsGitExecutionGatewayResult:
    allowed: bool
    reason: str
    ready_to_execute: bool
    performs_write: bool = False


def validate_finops_git_execution(
    commit_plan: FinOpsGitCommitDryRun,
) -> FinOpsGitExecutionGatewayResult:
    """
    Validate a FinOps Git commit dry-run before any future
    Git execution request is built.

    This gateway performs no write.
    """

    if not commit_plan.ready_to_commit:
        return FinOpsGitExecutionGatewayResult(
            allowed=False,
            reason=(
                "FinOps commit plan is not ready to commit."
            ),
            ready_to_execute=False,
            performs_write=False,
        )

    if commit_plan.performs_write:
        return FinOpsGitExecutionGatewayResult(
            allowed=False,
            reason=(
                "FinOps commit plan unexpectedly declares "
                "a write operation."
            ),
            ready_to_execute=False,
            performs_write=False,
        )

    if commit_plan.writes_file:
        return FinOpsGitExecutionGatewayResult(
            allowed=False,
            reason=(
                "FinOps commit plan must not write files "
                "before execution approval."
            ),
            ready_to_execute=False,
            performs_write=False,
        )

    if commit_plan.writes_git:
        return FinOpsGitExecutionGatewayResult(
            allowed=False,
            reason=(
                "FinOps commit plan must not write Git "
                "before execution approval."
            ),
            ready_to_execute=False,
            performs_write=False,
        )

    if not commit_plan.target_file.strip():
        return FinOpsGitExecutionGatewayResult(
            allowed=False,
            reason="FinOps target file is required.",
            ready_to_execute=False,
            performs_write=False,
        )

    if not commit_plan.branch_name.strip():
        return FinOpsGitExecutionGatewayResult(
            allowed=False,
            reason="FinOps branch name is required.",
            ready_to_execute=False,
            performs_write=False,
        )

    if not commit_plan.commit_message.strip():
        return FinOpsGitExecutionGatewayResult(
            allowed=False,
            reason="FinOps commit message is required.",
            ready_to_execute=False,
            performs_write=False,
        )

    if not commit_plan.rendered_yaml.strip():
        return FinOpsGitExecutionGatewayResult(
            allowed=False,
            reason="Rendered FinOps YAML is required.",
            ready_to_execute=False,
            performs_write=False,
        )

    if commit_plan.branch_name in {
        "main",
        "master",
        "develop",
    }:
        return FinOpsGitExecutionGatewayResult(
            allowed=False,
            reason=(
                "Direct execution against a protected "
                "base branch is not allowed."
            ),
            ready_to_execute=False,
            performs_write=False,
        )

    if not commit_plan.branch_name.startswith(
        "fix/finops-"
    ):
        return FinOpsGitExecutionGatewayResult(
            allowed=False,
            reason=(
                "FinOps branch name is outside the "
                "allowed naming policy."
            ),
            ready_to_execute=False,
            performs_write=False,
        )

    return FinOpsGitExecutionGatewayResult(
        allowed=True,
        reason=(
            "FinOps Git commit plan passed all "
            "execution safety checks."
        ),
        ready_to_execute=True,
        performs_write=False,
    )
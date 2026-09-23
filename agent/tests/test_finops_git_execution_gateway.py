from agent.finops_agent.git_commit_dry_run import (
    FinOpsGitCommitDryRun,
)
from agent.finops_agent.git_execution_gateway import (
    validate_finops_git_execution,
)


def _commit_plan() -> FinOpsGitCommitDryRun:
    return FinOpsGitCommitDryRun(
        target_file=(
            "gitops/apps/online-boutique/base/"
            "kubernetes-manifests.yaml"
        ),
        branch_name=(
            "fix/finops-checkoutservice-rightsizing"
        ),
        commit_message=(
            "fix(finops): rightsize checkoutservice"
        ),
        rendered_yaml=(
            "apiVersion: apps/v1\n"
            "kind: Deployment\n"
        ),
        ready_to_commit=True,
        performs_write=False,
        writes_file=False,
        writes_git=False,
    )


def test_valid_commit_plan_is_allowed():
    result = validate_finops_git_execution(
        _commit_plan(),
    )

    assert result.allowed is True
    assert result.ready_to_execute is True
    assert result.performs_write is False


def test_not_ready_commit_plan_is_blocked():
    plan = _commit_plan()

    invalid = FinOpsGitCommitDryRun(
        target_file=plan.target_file,
        branch_name=plan.branch_name,
        commit_message=plan.commit_message,
        rendered_yaml=plan.rendered_yaml,
        ready_to_commit=False,
        performs_write=False,
        writes_file=False,
        writes_git=False,
    )

    result = validate_finops_git_execution(
        invalid,
    )

    assert result.allowed is False
    assert result.ready_to_execute is False


def test_performs_write_flag_is_blocked():
    plan = _commit_plan()

    invalid = FinOpsGitCommitDryRun(
        target_file=plan.target_file,
        branch_name=plan.branch_name,
        commit_message=plan.commit_message,
        rendered_yaml=plan.rendered_yaml,
        ready_to_commit=True,
        performs_write=True,
        writes_file=False,
        writes_git=False,
    )

    result = validate_finops_git_execution(
        invalid,
    )

    assert result.allowed is False
    assert result.ready_to_execute is False


def test_file_write_flag_is_blocked():
    plan = _commit_plan()

    invalid = FinOpsGitCommitDryRun(
        target_file=plan.target_file,
        branch_name=plan.branch_name,
        commit_message=plan.commit_message,
        rendered_yaml=plan.rendered_yaml,
        ready_to_commit=True,
        performs_write=False,
        writes_file=True,
        writes_git=False,
    )

    result = validate_finops_git_execution(
        invalid,
    )

    assert result.allowed is False


def test_git_write_flag_is_blocked():
    plan = _commit_plan()

    invalid = FinOpsGitCommitDryRun(
        target_file=plan.target_file,
        branch_name=plan.branch_name,
        commit_message=plan.commit_message,
        rendered_yaml=plan.rendered_yaml,
        ready_to_commit=True,
        performs_write=False,
        writes_file=False,
        writes_git=True,
    )

    result = validate_finops_git_execution(
        invalid,
    )

    assert result.allowed is False


def test_missing_target_file_is_blocked():
    plan = _commit_plan()

    invalid = FinOpsGitCommitDryRun(
        target_file="   ",
        branch_name=plan.branch_name,
        commit_message=plan.commit_message,
        rendered_yaml=plan.rendered_yaml,
        ready_to_commit=True,
        performs_write=False,
        writes_file=False,
        writes_git=False,
    )

    result = validate_finops_git_execution(
        invalid,
    )

    assert result.allowed is False
    assert "target file" in result.reason


def test_missing_branch_name_is_blocked():
    plan = _commit_plan()

    invalid = FinOpsGitCommitDryRun(
        target_file=plan.target_file,
        branch_name="   ",
        commit_message=plan.commit_message,
        rendered_yaml=plan.rendered_yaml,
        ready_to_commit=True,
        performs_write=False,
        writes_file=False,
        writes_git=False,
    )

    result = validate_finops_git_execution(
        invalid,
    )

    assert result.allowed is False
    assert "branch name" in result.reason


def test_missing_commit_message_is_blocked():
    plan = _commit_plan()

    invalid = FinOpsGitCommitDryRun(
        target_file=plan.target_file,
        branch_name=plan.branch_name,
        commit_message="   ",
        rendered_yaml=plan.rendered_yaml,
        ready_to_commit=True,
        performs_write=False,
        writes_file=False,
        writes_git=False,
    )

    result = validate_finops_git_execution(
        invalid,
    )

    assert result.allowed is False
    assert "commit message" in result.reason


def test_missing_rendered_yaml_is_blocked():
    plan = _commit_plan()

    invalid = FinOpsGitCommitDryRun(
        target_file=plan.target_file,
        branch_name=plan.branch_name,
        commit_message=plan.commit_message,
        rendered_yaml="   ",
        ready_to_commit=True,
        performs_write=False,
        writes_file=False,
        writes_git=False,
    )

    result = validate_finops_git_execution(
        invalid,
    )

    assert result.allowed is False
    assert "Rendered FinOps YAML" in result.reason


def test_protected_branch_is_blocked():
    plan = _commit_plan()

    invalid = FinOpsGitCommitDryRun(
        target_file=plan.target_file,
        branch_name="main",
        commit_message=plan.commit_message,
        rendered_yaml=plan.rendered_yaml,
        ready_to_commit=True,
        performs_write=False,
        writes_file=False,
        writes_git=False,
    )

    result = validate_finops_git_execution(
        invalid,
    )

    assert result.allowed is False
    assert result.ready_to_execute is False


def test_branch_outside_finops_policy_is_blocked():
    plan = _commit_plan()

    invalid = FinOpsGitCommitDryRun(
        target_file=plan.target_file,
        branch_name="feature/random-change",
        commit_message=plan.commit_message,
        rendered_yaml=plan.rendered_yaml,
        ready_to_commit=True,
        performs_write=False,
        writes_file=False,
        writes_git=False,
    )

    result = validate_finops_git_execution(
        invalid,
    )

    assert result.allowed is False
    assert "naming policy" in result.reason
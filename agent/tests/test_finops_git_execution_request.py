import pytest

from agent.finops_agent.git_commit_dry_run import (
    FinOpsGitCommitDryRun,
)
from agent.finops_agent.git_execution_gateway import (
    FinOpsGitExecutionGatewayResult,
)
from agent.finops_agent.git_execution_request import (
    _is_safe_target_file,
    build_finops_git_execution_request,
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
            "metadata:\n"
            "  name: checkoutservice\n"
        ),
        ready_to_commit=True,
        performs_write=False,
        writes_file=False,
        writes_git=False,
    )


def _gateway() -> FinOpsGitExecutionGatewayResult:
    return FinOpsGitExecutionGatewayResult(
        allowed=True,
        reason="Safety checks passed.",
        ready_to_execute=True,
        performs_write=False,
    )


def test_build_finops_git_execution_request():
    result = build_finops_git_execution_request(
        commit_plan=_commit_plan(),
        gateway=_gateway(),
        repository="stevvv2005/kubepilot",
        base_branch="main",
    )

    assert (
        result.repository
        == "stevvv2005/kubepilot"
    )

    assert result.base_branch == "main"

    assert (
        result.head_branch
        == "fix/finops-checkoutservice-rightsizing"
    )

    assert (
        result.target_file
        == (
            "gitops/apps/online-boutique/base/"
            "kubernetes-manifests.yaml"
        )
    )

    assert (
        result.commit_message
        == "fix(finops): rightsize checkoutservice"
    )

    assert (
        result.pr_title
        == result.commit_message
    )

    assert (
        "KubePilot FinOps Rightsizing"
        in result.pr_body
    )

    assert result.create_branch is True
    assert result.write_file is True
    assert result.create_commit is True
    assert result.push_branch is True
    assert result.create_pr is True

    assert result.authorized is True

    # Important:
    # these booleans describe future operations.
    # Nothing is executed by this builder.
    assert result.performs_write is False


def test_gateway_must_allow_execution():
    gateway = FinOpsGitExecutionGatewayResult(
        allowed=False,
        reason="blocked",
        ready_to_execute=False,
        performs_write=False,
    )

    with pytest.raises(
        ValueError,
        match="did not allow",
    ):
        build_finops_git_execution_request(
            commit_plan=_commit_plan(),
            gateway=gateway,
            repository="stevvv2005/kubepilot",
        )


def test_gateway_must_be_ready():
    gateway = FinOpsGitExecutionGatewayResult(
        allowed=True,
        reason="not ready",
        ready_to_execute=False,
        performs_write=False,
    )

    with pytest.raises(
        ValueError,
        match="gateway is not ready",
    ):
        build_finops_git_execution_request(
            commit_plan=_commit_plan(),
            gateway=gateway,
            repository="stevvv2005/kubepilot",
        )


def test_gateway_write_flag_is_rejected():
    gateway = FinOpsGitExecutionGatewayResult(
        allowed=True,
        reason="invalid",
        ready_to_execute=True,
        performs_write=True,
    )

    with pytest.raises(
        ValueError,
        match="must not perform writes",
    ):
        build_finops_git_execution_request(
            commit_plan=_commit_plan(),
            gateway=gateway,
            repository="stevvv2005/kubepilot",
        )


def test_empty_repository_is_rejected():
    with pytest.raises(
        ValueError,
        match="Repository is required",
    ):
        build_finops_git_execution_request(
            commit_plan=_commit_plan(),
            gateway=_gateway(),
            repository="   ",
        )


def test_empty_base_branch_is_rejected():
    with pytest.raises(
        ValueError,
        match="Base branch is required",
    ):
        build_finops_git_execution_request(
            commit_plan=_commit_plan(),
            gateway=_gateway(),
            repository="stevvv2005/kubepilot",
            base_branch="   ",
        )


def test_head_branch_must_differ_from_base():
    plan = _commit_plan()

    invalid = FinOpsGitCommitDryRun(
        target_file=plan.target_file,
        branch_name="fix/finops-checkoutservice-rightsizing",
        commit_message=plan.commit_message,
        rendered_yaml=plan.rendered_yaml,
        ready_to_commit=True,
        performs_write=False,
        writes_file=False,
        writes_git=False,
    )

    with pytest.raises(
        ValueError,
        match="must differ from base branch",
    ):
        build_finops_git_execution_request(
            commit_plan=invalid,
            gateway=_gateway(),
            repository="stevvv2005/kubepilot",
            base_branch=(
                "fix/finops-checkoutservice-rightsizing"
            ),
        )


def test_head_branch_must_follow_finops_policy():
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

    with pytest.raises(
        ValueError,
        match="outside the FinOps branch policy",
    ):
        build_finops_git_execution_request(
            commit_plan=invalid,
            gateway=_gateway(),
            repository="stevvv2005/kubepilot",
        )


def test_unsafe_target_paths_are_rejected():
    assert (
        _is_safe_target_file(
            "gitops/apps/app.yaml"
        )
        is True
    )

    assert (
        _is_safe_target_file(
            "../secret.yaml"
        )
        is False
    )

    assert (
        _is_safe_target_file(
            "gitops/../../secret.yaml"
        )
        is False
    )


def test_commit_plan_write_flags_are_rejected():
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

    with pytest.raises(
        ValueError,
        match="unexpected write flags",
    ):
        build_finops_git_execution_request(
            commit_plan=invalid,
            gateway=_gateway(),
            repository="stevvv2005/kubepilot",
        )
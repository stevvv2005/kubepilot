import pytest

from agent.finops_agent.git_execution_request import (
    FinOpsGitExecutionRequest,
)
from agent.finops_agent.git_executor import (
    execute_finops_git_request,
)


def _request() -> FinOpsGitExecutionRequest:
    return FinOpsGitExecutionRequest(
        repository="stevvv2005/kubepilot",
        base_branch="main",
        head_branch=(
            "fix/finops-checkoutservice-rightsizing"
        ),
        target_file=(
            "gitops/apps/online-boutique/base/"
            "kubernetes-manifests.yaml"
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
        pr_title=(
            "fix(finops): rightsize checkoutservice"
        ),
        pr_body="FinOps rightsizing PR",
        create_branch=True,
        write_file=True,
        create_commit=True,
        push_branch=True,
        create_pr=True,
        authorized=True,
        performs_write=False,
    )


def test_finops_git_executor_dry_run():
    result = execute_finops_git_request(
        request=_request(),
        dry_run=True,
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

    assert result.dry_run is True

    assert result.would_create_branch is True
    assert result.would_write_file is True
    assert result.would_create_commit is True
    assert result.would_push_branch is True
    assert result.would_create_pr is True

    assert result.executed is False
    assert result.performs_write is False


def test_real_execution_is_disabled():
    with pytest.raises(
        ValueError,
        match="Real FinOps Git execution is disabled",
    ):
        execute_finops_git_request(
            request=_request(),
            dry_run=False,
        )


def test_unauthorized_request_is_rejected():
    request = _request()

    invalid = FinOpsGitExecutionRequest(
        repository=request.repository,
        base_branch=request.base_branch,
        head_branch=request.head_branch,
        target_file=request.target_file,
        commit_message=request.commit_message,
        rendered_yaml=request.rendered_yaml,
        pr_title=request.pr_title,
        pr_body=request.pr_body,
        create_branch=request.create_branch,
        write_file=request.write_file,
        create_commit=request.create_commit,
        push_branch=request.push_branch,
        create_pr=request.create_pr,
        authorized=False,
        performs_write=False,
    )

    with pytest.raises(
        ValueError,
        match="not authorized",
    ):
        execute_finops_git_request(
            request=invalid,
            dry_run=True,
        )


def test_request_write_flag_is_rejected():
    request = _request()

    invalid = FinOpsGitExecutionRequest(
        repository=request.repository,
        base_branch=request.base_branch,
        head_branch=request.head_branch,
        target_file=request.target_file,
        commit_message=request.commit_message,
        rendered_yaml=request.rendered_yaml,
        pr_title=request.pr_title,
        pr_body=request.pr_body,
        create_branch=request.create_branch,
        write_file=request.write_file,
        create_commit=request.create_commit,
        push_branch=request.push_branch,
        create_pr=request.create_pr,
        authorized=True,
        performs_write=True,
    )

    with pytest.raises(
        ValueError,
        match="unexpectedly declares a write",
    ):
        execute_finops_git_request(
            request=invalid,
            dry_run=True,
        )


def test_missing_repository_is_rejected():
    request = _request()

    invalid = FinOpsGitExecutionRequest(
        repository="   ",
        base_branch=request.base_branch,
        head_branch=request.head_branch,
        target_file=request.target_file,
        commit_message=request.commit_message,
        rendered_yaml=request.rendered_yaml,
        pr_title=request.pr_title,
        pr_body=request.pr_body,
        create_branch=request.create_branch,
        write_file=request.write_file,
        create_commit=request.create_commit,
        push_branch=request.push_branch,
        create_pr=request.create_pr,
        authorized=True,
        performs_write=False,
    )

    with pytest.raises(
        ValueError,
        match="Repository is required",
    ):
        execute_finops_git_request(
            request=invalid,
        )


def test_missing_base_branch_is_rejected():
    request = _request()

    invalid = FinOpsGitExecutionRequest(
        repository=request.repository,
        base_branch="   ",
        head_branch=request.head_branch,
        target_file=request.target_file,
        commit_message=request.commit_message,
        rendered_yaml=request.rendered_yaml,
        pr_title=request.pr_title,
        pr_body=request.pr_body,
        create_branch=request.create_branch,
        write_file=request.write_file,
        create_commit=request.create_commit,
        push_branch=request.push_branch,
        create_pr=request.create_pr,
        authorized=True,
        performs_write=False,
    )

    with pytest.raises(
        ValueError,
        match="Base branch is required",
    ):
        execute_finops_git_request(
            request=invalid,
        )


def test_missing_head_branch_is_rejected():
    request = _request()

    invalid = FinOpsGitExecutionRequest(
        repository=request.repository,
        base_branch=request.base_branch,
        head_branch="   ",
        target_file=request.target_file,
        commit_message=request.commit_message,
        rendered_yaml=request.rendered_yaml,
        pr_title=request.pr_title,
        pr_body=request.pr_body,
        create_branch=request.create_branch,
        write_file=request.write_file,
        create_commit=request.create_commit,
        push_branch=request.push_branch,
        create_pr=request.create_pr,
        authorized=True,
        performs_write=False,
    )

    with pytest.raises(
        ValueError,
        match="Head branch is required",
    ):
        execute_finops_git_request(
            request=invalid,
        )


def test_head_branch_must_differ_from_base():
    request = _request()

    invalid = FinOpsGitExecutionRequest(
        repository=request.repository,
        base_branch="main",
        head_branch="main",
        target_file=request.target_file,
        commit_message=request.commit_message,
        rendered_yaml=request.rendered_yaml,
        pr_title=request.pr_title,
        pr_body=request.pr_body,
        create_branch=request.create_branch,
        write_file=request.write_file,
        create_commit=request.create_commit,
        push_branch=request.push_branch,
        create_pr=request.create_pr,
        authorized=True,
        performs_write=False,
    )

    with pytest.raises(
        ValueError,
        match="must differ from base branch",
    ):
        execute_finops_git_request(
            request=invalid,
        )


def test_head_branch_policy_is_enforced():
    request = _request()

    invalid = FinOpsGitExecutionRequest(
        repository=request.repository,
        base_branch=request.base_branch,
        head_branch="feature/random-change",
        target_file=request.target_file,
        commit_message=request.commit_message,
        rendered_yaml=request.rendered_yaml,
        pr_title=request.pr_title,
        pr_body=request.pr_body,
        create_branch=request.create_branch,
        write_file=request.write_file,
        create_commit=request.create_commit,
        push_branch=request.push_branch,
        create_pr=request.create_pr,
        authorized=True,
        performs_write=False,
    )

    with pytest.raises(
        ValueError,
        match="outside the FinOps branch policy",
    ):
        execute_finops_git_request(
            request=invalid,
        )


def test_missing_target_file_is_rejected():
    request = _request()

    invalid = FinOpsGitExecutionRequest(
        repository=request.repository,
        base_branch=request.base_branch,
        head_branch=request.head_branch,
        target_file="   ",
        commit_message=request.commit_message,
        rendered_yaml=request.rendered_yaml,
        pr_title=request.pr_title,
        pr_body=request.pr_body,
        create_branch=request.create_branch,
        write_file=request.write_file,
        create_commit=request.create_commit,
        push_branch=request.push_branch,
        create_pr=request.create_pr,
        authorized=True,
        performs_write=False,
    )

    with pytest.raises(
        ValueError,
        match="Target file is required",
    ):
        execute_finops_git_request(
            request=invalid,
        )


def test_missing_commit_message_is_rejected():
    request = _request()

    invalid = FinOpsGitExecutionRequest(
        repository=request.repository,
        base_branch=request.base_branch,
        head_branch=request.head_branch,
        target_file=request.target_file,
        commit_message="   ",
        rendered_yaml=request.rendered_yaml,
        pr_title=request.pr_title,
        pr_body=request.pr_body,
        create_branch=request.create_branch,
        write_file=request.write_file,
        create_commit=request.create_commit,
        push_branch=request.push_branch,
        create_pr=request.create_pr,
        authorized=True,
        performs_write=False,
    )

    with pytest.raises(
        ValueError,
        match="Commit message is required",
    ):
        execute_finops_git_request(
            request=invalid,
        )


def test_missing_rendered_yaml_is_rejected():
    request = _request()

    invalid = FinOpsGitExecutionRequest(
        repository=request.repository,
        base_branch=request.base_branch,
        head_branch=request.head_branch,
        target_file=request.target_file,
        commit_message=request.commit_message,
        rendered_yaml="   ",
        pr_title=request.pr_title,
        pr_body=request.pr_body,
        create_branch=request.create_branch,
        write_file=request.write_file,
        create_commit=request.create_commit,
        push_branch=request.push_branch,
        create_pr=request.create_pr,
        authorized=True,
        performs_write=False,
    )

    with pytest.raises(
        ValueError,
        match="Rendered YAML is required",
    ):
        execute_finops_git_request(
            request=invalid,
        )
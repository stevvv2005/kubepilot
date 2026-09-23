from dataclasses import replace

import pytest

from agent.sre_agent.git_commit_dry_run import GitCommitDryRun
from agent.sre_agent.git_execution_gateway import (
    GitExecutionGatewayResult,
)
from agent.sre_agent.git_execution_request import (
    build_git_execution_request,
)
from agent.sre_agent.github_request import (
    GitHubPullRequestRequest,
)


def build_commit_plan() -> GitCommitDryRun:
    return GitCommitDryRun(
        target_file="chaos/oomkilled-pod.yaml",
        branch_name="fix/sre-oomkilled",
        commit_message="fix(sre): remediate OOMKilled",
        rendered_yaml=(
            "apiVersion: v1\n"
            "kind: Pod\n"
            "metadata:\n"
            "  name: kubepilot-oomkilled\n"
            "spec:\n"
            "  containers:\n"
            "  - name: memory-hog\n"
            "    resources:\n"
            "      limits:\n"
            "        memory: 64Mi\n"
        ),
        ready_to_commit=True,
        performs_write=False,
        writes_file=False,
        writes_git=False,
    )


def build_execution_gateway() -> GitExecutionGatewayResult:
    return GitExecutionGatewayResult(
        allowed=True,
        reason="Git execution passed all safety checks.",
        ready_to_execute=True,
        performs_write=False,
    )


def build_github_request() -> GitHubPullRequestRequest:
    return GitHubPullRequestRequest(
        repository="stevvv2005/kubepilot",
        base_branch="main",
        head_branch="fix/sre-oomkilled",
        title="fix(sre): remediate OOMKilled",
        body="Approved OOMKilled remediation.",
        target_file="chaos/oomkilled-pod.yaml",
        approved_value="64Mi",
        ready_to_send=True,
        performs_write=False,
    )


def test_build_authorized_git_execution_request():
    result = build_git_execution_request(
        commit_plan=build_commit_plan(),
        execution_gateway=build_execution_gateway(),
        github_request=build_github_request(),
    )

    assert result.repository == "stevvv2005/kubepilot"
    assert result.base_branch == "main"
    assert result.head_branch == "fix/sre-oomkilled"

    assert result.target_file == "chaos/oomkilled-pod.yaml"
    assert result.commit_message == (
        "fix(sre): remediate OOMKilled"
    )

    assert "memory: 64Mi" in result.rendered_yaml

    assert result.pr_title == (
        "fix(sre): remediate OOMKilled"
    )

    assert result.create_branch is True
    assert result.write_file is True
    assert result.create_commit is True
    assert result.push_branch is True
    assert result.create_pr is True

    assert result.authorized is True

    # Request describes future writes,
    # but this builder itself performs none.
    assert result.performs_write is False


def test_gateway_must_authorize_execution():
    gateway = replace(
        build_execution_gateway(),
        allowed=False,
        ready_to_execute=False,
    )

    with pytest.raises(
        ValueError,
        match="did not authorize",
    ):
        build_git_execution_request(
            commit_plan=build_commit_plan(),
            execution_gateway=gateway,
            github_request=build_github_request(),
        )


def test_commit_plan_must_be_ready():
    commit_plan = replace(
        build_commit_plan(),
        ready_to_commit=False,
    )

    with pytest.raises(
        ValueError,
        match="commit plan is not ready",
    ):
        build_git_execution_request(
            commit_plan=commit_plan,
            execution_gateway=build_execution_gateway(),
            github_request=build_github_request(),
        )


def test_github_request_must_be_ready():
    github_request = replace(
        build_github_request(),
        ready_to_send=False,
    )

    with pytest.raises(
        ValueError,
        match="request is not ready",
    ):
        build_git_execution_request(
            commit_plan=build_commit_plan(),
            execution_gateway=build_execution_gateway(),
            github_request=github_request,
        )


def test_target_file_must_match():
    github_request = replace(
        build_github_request(),
        target_file="chaos/other.yaml",
    )

    with pytest.raises(
        ValueError,
        match="target file does not match",
    ):
        build_git_execution_request(
            commit_plan=build_commit_plan(),
            execution_gateway=build_execution_gateway(),
            github_request=github_request,
        )


def test_branch_must_match():
    github_request = replace(
        build_github_request(),
        head_branch="fix/sre-wrong-branch",
    )

    with pytest.raises(
        ValueError,
        match="branch does not match",
    ):
        build_git_execution_request(
            commit_plan=build_commit_plan(),
            execution_gateway=build_execution_gateway(),
            github_request=github_request,
        )

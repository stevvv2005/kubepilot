from dataclasses import replace

import pytest

from agent.sre_agent.git_execution_request import GitExecutionRequest
from agent.sre_agent.git_executor import execute_git_request


def build_execution_request() -> GitExecutionRequest:
    return GitExecutionRequest(
        repository="stevvv2005/kubepilot",
        base_branch="main",
        head_branch="fix/sre-oomkilled",
        target_file="chaos/oomkilled-pod.yaml",
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
        pr_title="fix(sre): remediate OOMKilled",
        pr_body="Approved remediation.",
        create_branch=True,
        write_file=True,
        create_commit=True,
        push_branch=True,
        create_pr=True,
        authorized=True,
        performs_write=False,
    )


def test_executor_dry_run_describes_all_operations():
    result = execute_git_request(
        request=build_execution_request(),
    )

    assert result.repository == "stevvv2005/kubepilot"
    assert result.base_branch == "main"
    assert result.head_branch == "fix/sre-oomkilled"
    assert result.target_file == "chaos/oomkilled-pod.yaml"

    assert result.commit_message == (
        "fix(sre): remediate OOMKilled"
    )

    assert result.dry_run is True

    assert result.would_create_branch is True
    assert result.would_write_file is True
    assert result.would_create_commit is True
    assert result.would_push_branch is True
    assert result.would_create_pr is True

    assert result.executed is False
    assert result.performs_write is False


def test_executor_rejects_unauthorized_request():
    request = replace(
        build_execution_request(),
        authorized=False,
    )

    with pytest.raises(
        ValueError,
        match="not authorized",
    ):
        execute_git_request(
            request=request,
        )


def test_executor_rejects_unexpected_write_flag():
    request = replace(
        build_execution_request(),
        performs_write=True,
    )

    with pytest.raises(
        ValueError,
        match="Unexpected write flag",
    ):
        execute_git_request(
            request=request,
        )


def test_real_execution_is_disabled():
    with pytest.raises(
        ValueError,
        match="Real Git execution is disabled",
    ):
        execute_git_request(
            request=build_execution_request(),
            dry_run=False,
        )


def test_executor_requires_rendered_yaml():
    request = replace(
        build_execution_request(),
        rendered_yaml="",
    )

    with pytest.raises(
        ValueError,
        match="Rendered YAML is required",
    ):
        execute_git_request(
            request=request,
        )


def test_executor_does_not_perform_write():
    result = execute_git_request(
        request=build_execution_request(),
        dry_run=True,
    )

    assert result.executed is False
    assert result.performs_write is False

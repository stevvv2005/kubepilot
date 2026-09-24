from dataclasses import replace

import pytest

from agent.sre_agent.git_execution_request import GitExecutionRequest
from agent.sre_agent.github_execution_gateway import (
    validate_sre_github_execution,
)


def _request() -> GitExecutionRequest:
    return GitExecutionRequest(
        repository="stevvv2005/kubepilot",
        base_branch="main",
        head_branch="fix/sre-oomkilled",
        target_file="chaos/oomkilled-pod.yaml",
        commit_message="fix(sre): remediate OOMKilled",
        rendered_yaml=(
            "apiVersion: v1\n"
            "kind: Pod\n"
        ),
        pr_title="fix(sre): remediate OOMKilled",
        pr_body="Human-approved SRE change.",
        create_branch=True,
        write_file=True,
        create_commit=True,
        push_branch=True,
        create_pr=True,
        authorized=True,
        performs_write=False,
    )


def test_sre_github_execution_allowed():
    result = validate_sre_github_execution(
        request=_request(),
        live_authorized=True,
    )

    assert result.allowed is True
    assert result.ready_to_execute is True
    assert result.performs_cluster_write is False


def test_sre_github_execution_requires_live_authorization():
    result = validate_sre_github_execution(
        request=_request(),
        live_authorized=False,
    )

    assert result.allowed is False
    assert result.ready_to_execute is False
    assert "explicit authorization" in result.reason


def test_sre_github_execution_rejects_missing_approval():
    result = validate_sre_github_execution(
        request=replace(
            _request(),
            authorized=False,
        ),
        live_authorized=True,
    )

    assert result.allowed is False
    assert "not authorized" in result.reason


def test_sre_github_execution_rejects_wrong_repository():
    result = validate_sre_github_execution(
        request=replace(
            _request(),
            repository="other/repo",
        ),
        live_authorized=True,
    )

    assert result.allowed is False
    assert "Repository" in result.reason


def test_sre_github_execution_rejects_wrong_base_branch():
    result = validate_sre_github_execution(
        request=replace(
            _request(),
            base_branch="develop",
        ),
        live_authorized=True,
    )

    assert result.allowed is False
    assert "Base branch" in result.reason


def test_sre_github_execution_rejects_invalid_branch():
    result = validate_sre_github_execution(
        request=replace(
            _request(),
            head_branch="feature/oomkilled",
        ),
        live_authorized=True,
    )

    assert result.allowed is False
    assert "branch policy" in result.reason


@pytest.mark.parametrize(
    "head_branch",
    [
        "fix/sre-",
        "fix/sre-OOMKilled",
        "fix/sre-oomkilled..retry",
        "fix/sre-oomkilled/ retry",
        "fix/sre-oomkilled.lock",
    ],
)
def test_sre_github_execution_rejects_malformed_fix_branch(
    head_branch,
):
    result = validate_sre_github_execution(
        request=replace(
            _request(),
            head_branch=head_branch,
        ),
        live_authorized=True,
    )

    assert result.allowed is False
    assert "branch policy" in result.reason


def test_sre_github_execution_rejects_non_allowlisted_target():
    result = validate_sre_github_execution(
        request=replace(
            _request(),
            target_file="chaos/untrusted.yaml",
        ),
        live_authorized=True,
    )

    assert result.allowed is False
    assert "allowlist" in result.reason


def test_sre_github_execution_rejects_empty_rendered_yaml():
    result = validate_sre_github_execution(
        request=replace(
            _request(),
            rendered_yaml=" ",
        ),
        live_authorized=True,
    )

    assert result.allowed is False
    assert "Rendered YAML" in result.reason


def test_sre_github_execution_rejects_unexpected_write_flag():
    result = validate_sre_github_execution(
        request=replace(
            _request(),
            performs_write=True,
        ),
        live_authorized=True,
    )

    assert result.allowed is False
    assert "direct write" in result.reason


def test_sre_github_execution_rejects_unexpected_operation_flags():
    result = validate_sre_github_execution(
        request=replace(
            _request(),
            create_pr=False,
        ),
        live_authorized=True,
    )

    assert result.allowed is False
    assert "PR creation" in result.reason

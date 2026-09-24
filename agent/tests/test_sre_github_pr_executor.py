from dataclasses import replace

import pytest

from agent.sre_agent.git_execution_request import GitExecutionRequest
from agent.sre_agent.github_pr_executor import (
    execute_sre_github_pr_request,
)


class FakeGitHubClient:
    def __init__(self):
        self.calls = []

    def get_branch_sha(
        self,
        *,
        repository,
        branch,
    ):
        self.calls.append(
            (
                "get_branch_sha",
                repository,
                branch,
            )
        )

        return "base-sha-123"

    def create_branch(
        self,
        *,
        repository,
        branch,
        source_sha,
    ):
        self.calls.append(
            (
                "create_branch",
                repository,
                branch,
                source_sha,
            )
        )

    def update_file(
        self,
        *,
        repository,
        branch,
        path,
        content,
        message,
    ):
        self.calls.append(
            (
                "update_file",
                repository,
                branch,
                path,
                content,
                message,
            )
        )

        return "commit-sha-456"

    def create_pull_request(
        self,
        *,
        repository,
        base_branch,
        head_branch,
        title,
        body,
    ):
        self.calls.append(
            (
                "create_pull_request",
                repository,
                base_branch,
                head_branch,
                title,
                body,
            )
        )

        return (
            79,
            "https://github.com/stevvv2005/kubepilot/pull/79",
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
            "metadata:\n"
            "  name: kubepilot-oomkilled\n"
        ),
        pr_title="fix(sre): remediate OOMKilled",
        pr_body="Human-approved OOMKilled remediation.",
        create_branch=True,
        write_file=True,
        create_commit=True,
        push_branch=True,
        create_pr=True,
        authorized=True,
        performs_write=False,
    )


def test_sre_github_pr_execution_with_fake_client():
    client = FakeGitHubClient()

    result = execute_sre_github_pr_request(
        request=_request(),
        client=client,
        live_authorized=True,
    )

    assert result.executed is True
    assert result.repository == "stevvv2005/kubepilot"
    assert result.base_branch == "main"
    assert result.head_branch == "fix/sre-oomkilled"
    assert result.target_file == "chaos/oomkilled-pod.yaml"
    assert result.commit_sha == "commit-sha-456"
    assert result.pr_number == 79
    assert (
        result.pr_url
        == "https://github.com/stevvv2005/kubepilot/pull/79"
    )
    assert result.performs_cluster_write is False
    assert len(client.calls) == 4


def test_sre_github_pr_execution_requires_live_authorization():
    with pytest.raises(
        ValueError,
        match="explicit authorization",
    ):
        execute_sre_github_pr_request(
            request=_request(),
            client=FakeGitHubClient(),
            live_authorized=False,
        )


def test_sre_github_pr_execution_rejects_missing_approval():
    with pytest.raises(
        ValueError,
        match="not authorized",
    ):
        execute_sre_github_pr_request(
            request=replace(
                _request(),
                authorized=False,
            ),
            client=FakeGitHubClient(),
            live_authorized=True,
        )


def test_sre_github_pr_execution_rejects_wrong_repository():
    with pytest.raises(
        ValueError,
        match="Repository",
    ):
        execute_sre_github_pr_request(
            request=replace(
                _request(),
                repository="other/repo",
            ),
            client=FakeGitHubClient(),
            live_authorized=True,
        )


def test_sre_github_pr_execution_rejects_wrong_base_branch():
    with pytest.raises(
        ValueError,
        match="Base branch",
    ):
        execute_sre_github_pr_request(
            request=replace(
                _request(),
                base_branch="develop",
            ),
            client=FakeGitHubClient(),
            live_authorized=True,
        )


def test_sre_github_pr_execution_rejects_invalid_branch():
    with pytest.raises(
        ValueError,
        match="branch policy",
    ):
        execute_sre_github_pr_request(
            request=replace(
                _request(),
                head_branch="feature/sre-oomkilled",
            ),
            client=FakeGitHubClient(),
            live_authorized=True,
        )


def test_sre_github_pr_execution_rejects_non_allowlisted_target():
    with pytest.raises(
        ValueError,
        match="allowlist",
    ):
        execute_sre_github_pr_request(
            request=replace(
                _request(),
                target_file="chaos/untrusted.yaml",
            ),
            client=FakeGitHubClient(),
            live_authorized=True,
        )


def test_sre_github_pr_execution_rejects_empty_rendered_yaml():
    with pytest.raises(
        ValueError,
        match="Rendered YAML",
    ):
        execute_sre_github_pr_request(
            request=replace(
                _request(),
                rendered_yaml="",
            ),
            client=FakeGitHubClient(),
            live_authorized=True,
        )


def test_sre_github_pr_execution_rejects_unexpected_write_flag():
    with pytest.raises(
        ValueError,
        match="direct write",
    ):
        execute_sre_github_pr_request(
            request=replace(
                _request(),
                performs_write=True,
            ),
            client=FakeGitHubClient(),
            live_authorized=True,
        )

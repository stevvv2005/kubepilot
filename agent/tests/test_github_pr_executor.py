import pytest

from agent.finops_agent.git_execution_request import (
    FinOpsGitExecutionRequest,
)
from agent.finops_agent.github_pr_executor import (
    execute_github_pr_request,
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
            42,
            "https://github.com/example/repo/pull/42",
        )


def _request():
    return FinOpsGitExecutionRequest(
        repository="example/repo",
        base_branch="main",
        head_branch="fix/finops-checkoutservice",
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
        ),
        pr_title=(
            "fix(finops): rightsize checkoutservice"
        ),
        pr_body=(
            "Human-approved FinOps change."
        ),
        create_branch=True,
        write_file=True,
        create_commit=True,
        push_branch=True,
        create_pr=True,
        authorized=True,
        performs_write=False,
    )


def test_github_pr_execution():
    client = FakeGitHubClient()

    result = execute_github_pr_request(
        request=_request(),
        client=client,
        live_authorized=True,
    )

    assert result.executed is True

    assert (
        result.commit_sha
        == "commit-sha-456"
    )

    assert result.pr_number == 42

    assert (
        result.pr_url
        == "https://github.com/example/repo/pull/42"
    )

    assert (
        result.performs_cluster_write
        is False
    )

    assert len(client.calls) == 4


def test_github_pr_execution_requires_authorization():
    with pytest.raises(
        ValueError,
        match="explicit authorization",
    ):
        execute_github_pr_request(
            request=_request(),
            client=FakeGitHubClient(),
            live_authorized=False,
        )


def test_github_pr_execution_rejects_unauthorized_request():
    request = _request()

    unsafe_request = FinOpsGitExecutionRequest(
        **{
            **request.__dict__,
            "authorized": False,
        }
    )

    with pytest.raises(
        ValueError,
        match="not authorized",
    ):
        execute_github_pr_request(
            request=unsafe_request,
            client=FakeGitHubClient(),
            live_authorized=True,
        )


def test_github_pr_execution_rejects_bad_branch():
    request = _request()

    unsafe_request = FinOpsGitExecutionRequest(
        **{
            **request.__dict__,
            "head_branch": "main",
        }
    )

    with pytest.raises(
        ValueError,
        match="must differ",
    ):
        execute_github_pr_request(
            request=unsafe_request,
            client=FakeGitHubClient(),
            live_authorized=True,
        )


def test_github_pr_execution_rejects_branch_policy_violation():
    request = _request()

    unsafe_request = FinOpsGitExecutionRequest(
        **{
            **request.__dict__,
            "head_branch": "feature/random",
        }
    )

    with pytest.raises(
        ValueError,
        match="branch policy",
    ):
        execute_github_pr_request(
            request=unsafe_request,
            client=FakeGitHubClient(),
            live_authorized=True,
        )
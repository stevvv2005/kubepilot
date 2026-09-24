import json

import pytest

from agent.finops_agent.github_rest_client import (
    GitHubRESTClient,
    GitHubRESTConfig,
)


class FakeResponse:
    def __init__(
        self,
        payload,
    ):
        self._payload = payload

    def read(self):
        return json.dumps(
            self._payload
        ).encode("utf-8")


class FakeOpener:
    def __init__(
        self,
        responses,
    ):
        self.responses = list(
            responses
        )

        self.requests = []

    def __call__(
        self,
        request,
        timeout=None,
    ):
        self.requests.append(
            (
                request,
                timeout,
            )
        )

        if not self.responses:
            raise AssertionError(
                "Unexpected GitHub API request."
            )

        return FakeResponse(
            self.responses.pop(0)
        )


def _config():
    return GitHubRESTConfig(
        token="test-token",
    )


def test_github_rest_client_requires_token():
    with pytest.raises(
        ValueError,
        match="token is required",
    ):
        GitHubRESTClient(
            config=GitHubRESTConfig(
                token="",
            )
        )


def test_github_rest_client_rejects_unsupported_branch_prefix():
    with pytest.raises(
        ValueError,
        match="branch prefix",
    ):
        GitHubRESTClient(
            config=GitHubRESTConfig(
                token="test-token",
                branch_prefix="feature/",
            )
        )


def test_get_branch_sha():
    opener = FakeOpener(
        [
            {
                "object": {
                    "sha": "base-sha-123",
                }
            }
        ]
    )

    client = GitHubRESTClient(
        config=_config(),
        opener=opener,
    )

    sha = client.get_branch_sha(
        repository="stevvv2005/kubepilot",
        branch="main",
    )

    assert sha == "base-sha-123"

    assert len(opener.requests) == 1

    request, timeout = (
        opener.requests[0]
    )

    assert request.method == "GET"

    assert (
        "/repos/stevvv2005/kubepilot/"
        "git/ref/heads/main"
        in request.full_url
    )

    assert timeout == 10.0


def test_create_finops_branch():
    opener = FakeOpener(
        [
            {
                "ref": (
                    "refs/heads/"
                    "fix/finops-checkoutservice"
                )
            }
        ]
    )

    client = GitHubRESTClient(
        config=_config(),
        opener=opener,
    )

    client.create_branch(
        repository="stevvv2005/kubepilot",
        branch=(
            "fix/finops-checkoutservice"
        ),
        source_sha="base-sha-123",
    )

    request, _ = opener.requests[0]

    assert request.method == "POST"

    body = json.loads(
        request.data.decode("utf-8")
    )

    assert (
        body["ref"]
        == (
            "refs/heads/"
            "fix/finops-checkoutservice"
        )
    )

    assert (
        body["sha"]
        == "base-sha-123"
    )


def test_create_sre_branch_with_explicit_policy():
    opener = FakeOpener(
        [
            {
                "ref": "refs/heads/fix/sre-oomkilled",
            }
        ]
    )

    client = GitHubRESTClient(
        config=GitHubRESTConfig(
            token="test-token",
            branch_prefix="fix/sre-",
        ),
        opener=opener,
    )

    client.create_branch(
        repository="stevvv2005/kubepilot",
        branch="fix/sre-oomkilled",
        source_sha="base-sha-123",
    )

    request, _ = opener.requests[0]
    body = json.loads(
        request.data.decode("utf-8")
    )

    assert body["ref"] == "refs/heads/fix/sre-oomkilled"


def test_create_branch_rejects_bad_policy():
    client = GitHubRESTClient(
        config=_config(),
        opener=FakeOpener([]),
    )

    with pytest.raises(
        ValueError,
        match="branch policy",
    ):
        client.create_branch(
            repository=(
                "stevvv2005/kubepilot"
            ),
            branch="feature/random",
            source_sha="abc",
        )


def test_update_file_returns_commit_sha():
    opener = FakeOpener(
        [
            {
                "sha": "file-sha-123",
            },
            {
                "commit": {
                    "sha": (
                        "commit-sha-456"
                    ),
                }
            },
        ]
    )

    client = GitHubRESTClient(
        config=_config(),
        opener=opener,
    )

    commit_sha = client.update_file(
        repository="stevvv2005/kubepilot",
        branch=(
            "fix/finops-checkoutservice"
        ),
        path=(
            "gitops/apps/online-boutique/"
            "base/kubernetes-manifests.yaml"
        ),
        content=(
            "apiVersion: apps/v1\n"
        ),
        message=(
            "fix(finops): rightsize "
            "checkoutservice"
        ),
    )

    assert (
        commit_sha
        == "commit-sha-456"
    )

    assert len(opener.requests) == 2

    get_request, _ = (
        opener.requests[0]
    )

    put_request, _ = (
        opener.requests[1]
    )

    assert get_request.method == "GET"
    assert put_request.method == "PUT"

    body = json.loads(
        put_request.data.decode(
            "utf-8"
        )
    )

    assert (
        body["branch"]
        == (
            "fix/finops-checkoutservice"
        )
    )

    assert (
        body["sha"]
        == "file-sha-123"
    )


def test_create_pull_request():
    opener = FakeOpener(
        [
            {
                "number": 77,
                "html_url": (
                    "https://github.com/"
                    "stevvv2005/kubepilot/"
                    "pull/77"
                ),
            }
        ]
    )

    client = GitHubRESTClient(
        config=_config(),
        opener=opener,
    )

    number, url = (
        client.create_pull_request(
            repository=(
                "stevvv2005/kubepilot"
            ),
            base_branch="main",
            head_branch=(
                "fix/finops-checkoutservice"
            ),
            title=(
                "fix(finops): rightsize "
                "checkoutservice"
            ),
            body=(
                "Human-approved change."
            ),
        )
    )

    assert number == 77

    assert (
        url
        == (
            "https://github.com/"
            "stevvv2005/kubepilot/"
            "pull/77"
        )
    )

    request, _ = opener.requests[0]

    assert request.method == "POST"

    body = json.loads(
        request.data.decode("utf-8")
    )

    assert body["base"] == "main"

    assert (
        body["head"]
        == (
            "fix/finops-checkoutservice"
        )
    )

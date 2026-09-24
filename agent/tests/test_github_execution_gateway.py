from agent.finops_agent.git_execution_request import (
    FinOpsGitExecutionRequest,
)
from agent.finops_agent.github_execution_gateway import (
    validate_github_execution,
)


def _request():
    return FinOpsGitExecutionRequest(
        repository="stevvv2005/kubepilot",
        base_branch="main",
        head_branch=(
            "fix/finops-checkoutservice"
        ),
        target_file=(
            "gitops/apps/online-boutique/"
            "base/kubernetes-manifests.yaml"
        ),
        commit_message=(
            "fix(finops): rightsize "
            "checkoutservice"
        ),
        rendered_yaml=(
            "apiVersion: apps/v1\n"
        ),
        pr_title=(
            "fix(finops): rightsize "
            "checkoutservice"
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


def test_github_execution_allowed():
    result = validate_github_execution(
        request=_request(),
        live_authorized=True,
    )

    assert result.allowed is True
    assert result.ready_to_execute is True
    assert (
        result.performs_cluster_write
        is False
    )


def test_github_execution_requires_live_authorization():
    result = validate_github_execution(
        request=_request(),
        live_authorized=False,
    )

    assert result.allowed is False
    assert (
        result.ready_to_execute
        is False
    )


def test_github_execution_rejects_bad_branch():
    request = _request()

    unsafe = FinOpsGitExecutionRequest(
        **{
            **request.__dict__,
            "head_branch": "main",
        }
    )

    result = validate_github_execution(
        request=unsafe,
        live_authorized=True,
    )

    assert result.allowed is False
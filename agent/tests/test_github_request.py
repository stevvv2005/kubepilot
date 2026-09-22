from agent.sre_agent.github_pr import GitHubPRGatewayResult
from agent.sre_agent.github_request import build_github_pr_request
from agent.sre_agent.pr_payload import PullRequestPayload


def test_blocked_gateway_produces_not_ready_request():
    payload = PullRequestPayload(
        incident_type="OOMKilled",
        title="fix(sre): review OOMKilled remediation",
        branch_name="fix/sre-oomkilled-pending",
        target_file="chaos/oomkilled-pod.yaml",
        container_name="memory-hog",
        field="resources.limits.memory",
        current_value="memory: 32Mi",
        approved_value=None,
        commit_message="fix(sre): review OOMKilled remediation",
        pr_body="Human approval required.",
        ready_to_create=False,
    )

    gateway = GitHubPRGatewayResult(
        allowed=False,
        reason="Pull Request payload is not approved for creation.",
        ready_to_send=False,
    )

    request = build_github_pr_request(
        repository="stevvv2005/kubepilot",
        base_branch="main",
        payload=payload,
        gateway=gateway,
    )

    assert request.repository == "stevvv2005/kubepilot"
    assert request.base_branch == "main"
    assert request.head_branch == "fix/sre-oomkilled-pending"
    assert request.ready_to_send is False
    assert request.performs_write is False


def test_approved_gateway_produces_ready_request():
    payload = PullRequestPayload(
        incident_type="OOMKilled",
        title="fix(sre): remediate OOMKilled",
        branch_name="fix/sre-oomkilled",
        target_file="chaos/oomkilled-pod.yaml",
        container_name="memory-hog",
        field="resources.limits.memory",
        current_value="memory: 32Mi",
        approved_value="64Mi",
        commit_message="fix(sre): remediate OOMKilled",
        pr_body="Approved remediation.",
        ready_to_create=True,
    )

    gateway = GitHubPRGatewayResult(
        allowed=True,
        reason="Payload passed all GitHub PR safety checks.",
        ready_to_send=True,
    )

    request = build_github_pr_request(
        repository="stevvv2005/kubepilot",
        base_branch="main",
        payload=payload,
        gateway=gateway,
    )

    assert request.repository == "stevvv2005/kubepilot"
    assert request.base_branch == "main"
    assert request.head_branch == "fix/sre-oomkilled"
    assert request.title == "fix(sre): remediate OOMKilled"
    assert request.body == "Approved remediation."
    assert request.target_file == "chaos/oomkilled-pod.yaml"
    assert request.approved_value == "64Mi"
    assert request.ready_to_send is True
    assert request.performs_write is False


def test_gateway_must_be_both_allowed_and_ready():
    payload = PullRequestPayload(
        incident_type="OOMKilled",
        title="fix(sre): remediate OOMKilled",
        branch_name="fix/sre-oomkilled",
        target_file="chaos/oomkilled-pod.yaml",
        container_name="memory-hog",
        field="resources.limits.memory",
        current_value="memory: 32Mi",
        approved_value="64Mi",
        commit_message="fix(sre): remediate OOMKilled",
        pr_body="Approved remediation.",
        ready_to_create=True,
    )

    gateway = GitHubPRGatewayResult(
        allowed=True,
        reason="Gateway is not ready.",
        ready_to_send=False,
    )

    request = build_github_pr_request(
        repository="stevvv2005/kubepilot",
        base_branch="main",
        payload=payload,
        gateway=gateway,
    )

    assert request.ready_to_send is False
    assert request.performs_write is False

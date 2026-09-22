from agent.sre_agent.github_pr import validate_pr_payload_for_github
from agent.sre_agent.pr_payload import PullRequestPayload


def test_unapproved_payload_is_blocked():
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

    result = validate_pr_payload_for_github(payload)

    assert result.allowed is False
    assert result.ready_to_send is False
    assert result.performs_write is False
    assert "not approved" in result.reason


def test_missing_approved_value_is_blocked():
    payload = PullRequestPayload(
        incident_type="OOMKilled",
        title="fix(sre): remediate OOMKilled",
        branch_name="fix/sre-oomkilled",
        target_file="chaos/oomkilled-pod.yaml",
        container_name="memory-hog",
        field="resources.limits.memory",
        current_value="memory: 32Mi",
        approved_value=None,
        commit_message="fix(sre): remediate OOMKilled",
        pr_body="Approved remediation.",
        ready_to_create=True,
    )

    result = validate_pr_payload_for_github(payload)

    assert result.allowed is False
    assert result.ready_to_send is False
    assert result.performs_write is False
    assert "approved value" in result.reason


def test_approved_payload_passes_gateway():
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

    result = validate_pr_payload_for_github(payload)

    assert result.allowed is True
    assert result.ready_to_send is True
    assert result.performs_write is False
    assert result.reason == (
        "Payload passed all GitHub PR safety checks."
    )


def test_unexpected_git_write_flag_is_blocked():
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
        writes_git=True,
    )

    result = validate_pr_payload_for_github(payload)

    assert result.allowed is False
    assert result.ready_to_send is False
    assert result.performs_write is False
    assert "Git write flag" in result.reason


def test_unexpected_pr_creation_flag_is_blocked():
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
        creates_pr=True,
    )

    result = validate_pr_payload_for_github(payload)

    assert result.allowed is False
    assert result.ready_to_send is False
    assert result.performs_write is False
    assert "creation flag" in result.reason

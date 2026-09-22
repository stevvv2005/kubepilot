from agent.sre_agent.pr_payload import build_pr_payload
from agent.sre_agent.reviewed_patch import ReviewedPatchPayload


def test_pr_payload_is_blocked_without_human_approval():
    reviewed_patch = ReviewedPatchPayload(
        incident_type="OOMKilled",
        target_file="chaos/oomkilled-pod.yaml",
        container_name="memory-hog",
        field="resources.limits.memory",
        current_value="memory: 32Mi",
        candidate_value="64Mi",
        approved_value=None,
        reason="Increase memory conservatively.",
        confidence="medium",
        ready_for_pr=False,
    )

    payload = build_pr_payload(reviewed_patch)

    assert payload.incident_type == "OOMKilled"
    assert payload.ready_to_create is False
    assert payload.approved_value is None
    assert payload.writes_git is False
    assert payload.creates_pr is False
    assert "Human approval is still required" in payload.pr_body


def test_pr_payload_is_ready_after_human_approval():
    reviewed_patch = ReviewedPatchPayload(
        incident_type="OOMKilled",
        target_file="chaos/oomkilled-pod.yaml",
        container_name="memory-hog",
        field="resources.limits.memory",
        current_value="memory: 32Mi",
        candidate_value="64Mi",
        approved_value="64Mi",
        reason="Increase memory conservatively.",
        confidence="medium",
        ready_for_pr=True,
    )

    payload = build_pr_payload(reviewed_patch)

    assert payload.incident_type == "OOMKilled"
    assert payload.title == "fix(sre): remediate OOMKilled"
    assert payload.branch_name == "fix/sre-oomkilled"
    assert payload.target_file == "chaos/oomkilled-pod.yaml"
    assert payload.container_name == "memory-hog"
    assert payload.field == "resources.limits.memory"
    assert payload.current_value == "memory: 32Mi"
    assert payload.approved_value == "64Mi"
    assert payload.commit_message == "fix(sre): remediate OOMKilled"
    assert payload.ready_to_create is True
    assert payload.writes_git is False
    assert payload.creates_pr is False

    assert "Human approval was provided" in payload.pr_body
    assert "64Mi" in payload.pr_body
    assert "GitOps / ArgoCD" in payload.pr_body


def test_human_approved_different_value_is_reflected_in_pr():
    reviewed_patch = ReviewedPatchPayload(
        incident_type="OOMKilled",
        target_file="chaos/oomkilled-pod.yaml",
        container_name="memory-hog",
        field="resources.limits.memory",
        current_value="memory: 32Mi",
        candidate_value="64Mi",
        approved_value="96Mi",
        reason="Increase memory conservatively.",
        confidence="medium",
        ready_for_pr=True,
    )

    payload = build_pr_payload(reviewed_patch)

    assert payload.approved_value == "96Mi"
    assert "96Mi" in payload.pr_body
    assert payload.ready_to_create is True
    assert payload.creates_pr is False

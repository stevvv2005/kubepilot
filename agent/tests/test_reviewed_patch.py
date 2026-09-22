from agent.sre_agent.candidate_value import CandidateValue
from agent.sre_agent.patch_proposal import PatchProposal
from agent.sre_agent.reviewed_patch import build_reviewed_patch_payload


def test_candidate_without_human_approval_is_not_ready_for_pr():
    patch = PatchProposal(
        incident_type="OOMKilled",
        target_file="chaos/oomkilled-pod.yaml",
        container_name="memory-hog",
        field="resources.limits.memory",
        current_value="memory: 32Mi",
        proposed_value=None,
        reason="Adjust memory.",
    )

    candidate = CandidateValue(
        incident_type="OOMKilled",
        field="resources.limits.memory",
        current_value="memory: 32Mi",
        candidate_value="64Mi",
        reason="Increase memory conservatively.",
        confidence="medium",
    )

    reviewed = build_reviewed_patch_payload(
        patch_proposal=patch,
        candidate_value=candidate,
    )

    assert reviewed.candidate_value == "64Mi"
    assert reviewed.approved_value is None
    assert reviewed.ready_for_pr is False
    assert reviewed.requires_human_approval is True
    assert reviewed.writes_file is False
    assert reviewed.auto_apply is False


def test_human_approved_value_is_ready_for_pr():
    patch = PatchProposal(
        incident_type="OOMKilled",
        target_file="chaos/oomkilled-pod.yaml",
        container_name="memory-hog",
        field="resources.limits.memory",
        current_value="memory: 32Mi",
        proposed_value=None,
        reason="Adjust memory.",
    )

    candidate = CandidateValue(
        incident_type="OOMKilled",
        field="resources.limits.memory",
        current_value="memory: 32Mi",
        candidate_value="64Mi",
        reason="Increase memory conservatively.",
        confidence="medium",
    )

    reviewed = build_reviewed_patch_payload(
        patch_proposal=patch,
        candidate_value=candidate,
        approved_value="64Mi",
    )

    assert reviewed.candidate_value == "64Mi"
    assert reviewed.approved_value == "64Mi"
    assert reviewed.ready_for_pr is True
    assert reviewed.requires_human_approval is True
    assert reviewed.writes_file is False
    assert reviewed.auto_apply is False


def test_human_can_approve_different_value():
    patch = PatchProposal(
        incident_type="OOMKilled",
        target_file="chaos/oomkilled-pod.yaml",
        container_name="memory-hog",
        field="resources.limits.memory",
        current_value="memory: 32Mi",
        proposed_value=None,
        reason="Adjust memory.",
    )

    candidate = CandidateValue(
        incident_type="OOMKilled",
        field="resources.limits.memory",
        current_value="memory: 32Mi",
        candidate_value="64Mi",
        reason="Increase memory conservatively.",
        confidence="medium",
    )

    reviewed = build_reviewed_patch_payload(
        patch_proposal=patch,
        candidate_value=candidate,
        approved_value="96Mi",
    )

    assert reviewed.candidate_value == "64Mi"
    assert reviewed.approved_value == "96Mi"
    assert reviewed.ready_for_pr is True
    assert reviewed.auto_apply is False


def test_healthy_never_becomes_ready_for_pr():
    patch = PatchProposal(
        incident_type="Healthy",
        target_file=None,
        container_name=None,
        field="none",
        current_value=None,
        proposed_value=None,
        reason="No patch is required.",
    )

    candidate = CandidateValue(
        incident_type="Healthy",
        field="none",
        current_value=None,
        candidate_value=None,
        reason="No candidate value is required.",
        confidence="high",
    )

    reviewed = build_reviewed_patch_payload(
        patch_proposal=patch,
        candidate_value=candidate,
        approved_value="anything",
    )

    assert reviewed.incident_type == "Healthy"
    assert reviewed.ready_for_pr is False
    assert reviewed.writes_file is False
    assert reviewed.auto_apply is False

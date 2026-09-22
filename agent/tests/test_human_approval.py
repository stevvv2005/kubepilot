import pytest

from agent.sre_agent.candidate_value import CandidateValue
from agent.sre_agent.human_approval import (
    HumanApprovalDecision,
    apply_human_approval,
)
from agent.sre_agent.patch_proposal import PatchProposal


def build_oom_patch() -> PatchProposal:
    return PatchProposal(
        incident_type="OOMKilled",
        target_file="chaos/oomkilled-pod.yaml",
        container_name="memory-hog",
        field="resources.limits.memory",
        current_value="memory: 32Mi",
        proposed_value=None,
        reason="Adjust the memory limit after reviewing observed usage.",
    )


def build_oom_candidate() -> CandidateValue:
    return CandidateValue(
        incident_type="OOMKilled",
        field="resources.limits.memory",
        current_value="memory: 32Mi",
        candidate_value="64Mi",
        reason=(
            "Increase the memory limit conservatively "
            "from 32Mi to 64Mi for human review."
        ),
        confidence="medium",
    )


def test_human_can_approve_candidate_value():
    decision = HumanApprovalDecision(
        approved=True,
        approved_value="64Mi",
        reviewer="human-reviewer",
        reason="Memory increase reviewed and accepted.",
    )

    reviewed = apply_human_approval(
        patch_proposal=build_oom_patch(),
        candidate_value=build_oom_candidate(),
        decision=decision,
    )

    assert reviewed.approved_value == "64Mi"
    assert reviewed.ready_for_pr is True
    assert reviewed.writes_file is False
    assert reviewed.auto_apply is False


def test_human_can_approve_different_reviewed_value():
    decision = HumanApprovalDecision(
        approved=True,
        approved_value="96Mi",
        reviewer="human-reviewer",
        reason="Reviewer selected a larger safe limit.",
    )

    reviewed = apply_human_approval(
        patch_proposal=build_oom_patch(),
        candidate_value=build_oom_candidate(),
        decision=decision,
    )

    assert reviewed.candidate_value == "64Mi"
    assert reviewed.approved_value == "96Mi"
    assert reviewed.ready_for_pr is True
    assert reviewed.writes_file is False


def test_rejected_decision_does_not_enable_pr():
    decision = HumanApprovalDecision(
        approved=False,
        approved_value=None,
        reviewer="human-reviewer",
        reason="More investigation required.",
    )

    reviewed = apply_human_approval(
        patch_proposal=build_oom_patch(),
        candidate_value=build_oom_candidate(),
        decision=decision,
    )

    assert reviewed.approved_value is None
    assert reviewed.ready_for_pr is False
    assert reviewed.auto_apply is False


def test_approval_requires_reviewer():
    decision = HumanApprovalDecision(
        approved=True,
        approved_value="64Mi",
        reviewer="",
        reason="Approved.",
    )

    with pytest.raises(
        ValueError,
        match="reviewer identity",
    ):
        apply_human_approval(
            patch_proposal=build_oom_patch(),
            candidate_value=build_oom_candidate(),
            decision=decision,
        )


def test_approval_requires_value():
    decision = HumanApprovalDecision(
        approved=True,
        approved_value=None,
        reviewer="human-reviewer",
        reason="Approved.",
    )

    with pytest.raises(
        ValueError,
        match="approved value",
    ):
        apply_human_approval(
            patch_proposal=build_oom_patch(),
            candidate_value=build_oom_candidate(),
            decision=decision,
        )


def test_blank_approved_value_is_rejected():
    decision = HumanApprovalDecision(
        approved=True,
        approved_value="   ",
        reviewer="human-reviewer",
        reason="Approved.",
    )

    with pytest.raises(
        ValueError,
        match="cannot be empty",
    ):
        apply_human_approval(
            patch_proposal=build_oom_patch(),
            candidate_value=build_oom_candidate(),
            decision=decision,
        )

import pytest

from agent.finops_agent.gitops_diff import (
    GitOpsDiffProposal,
)
from agent.finops_agent.human_approval import (
    FinOpsApprovalDecision,
    apply_finops_approval,
)


def _diff() -> GitOpsDiffProposal:
    return GitOpsDiffProposal(
        namespace="default",
        workload_name="checkoutservice",
        workload_type="Deployment",
        target_file=(
            "gitops/apps/online-boutique/base/"
            "kubernetes-manifests.yaml"
        ),
        manifest_kind="Deployment",
        manifest_name="checkoutservice",
        container_name="server",
        current_cpu_request="100m",
        proposed_cpu_request="10m",
        current_memory_request="64Mi",
        proposed_memory_request="16Mi",
        estimated_monthly_savings_usd=0.62,
        reason="test",
        confidence="medium",
        requires_human_approval=True,
        writes_file=False,
        writes_git=False,
        auto_apply=False,
    )


def test_approve_finops_diff_with_proposed_values():
    result = apply_finops_approval(
        diff=_diff(),
        decision=FinOpsApprovalDecision(
            approved=True,
            reviewer="alice",
            reason="Reviewed and approved",
        ),
    )

    assert result.approved is True

    assert result.approved_cpu_request == "10m"
    assert result.approved_memory_request == "16Mi"

    assert result.ready_for_render is True

    assert result.requires_human_approval is True
    assert result.writes_file is False
    assert result.writes_git is False
    assert result.auto_apply is False


def test_human_can_override_proposed_values():
    result = apply_finops_approval(
        diff=_diff(),
        decision=FinOpsApprovalDecision(
            approved=True,
            reviewer="alice",
            reason="Use more conservative requests",
            approved_cpu_request="50m",
            approved_memory_request="32Mi",
        ),
    )

    assert result.approved is True

    assert result.proposed_cpu_request == "10m"
    assert result.approved_cpu_request == "50m"

    assert result.proposed_memory_request == "16Mi"
    assert result.approved_memory_request == "32Mi"

    assert result.ready_for_render is True


def test_rejected_finops_diff_is_not_ready():
    result = apply_finops_approval(
        diff=_diff(),
        decision=FinOpsApprovalDecision(
            approved=False,
            reviewer="alice",
            reason="Need more historical data",
        ),
    )

    assert result.approved is False

    assert result.approved_cpu_request is None
    assert result.approved_memory_request is None

    assert result.ready_for_render is False

    assert result.writes_file is False
    assert result.writes_git is False
    assert result.auto_apply is False


def test_reviewer_is_required():
    with pytest.raises(
        ValueError,
        match="Reviewer is required",
    ):
        apply_finops_approval(
            diff=_diff(),
            decision=FinOpsApprovalDecision(
                approved=True,
                reviewer="   ",
                reason="approved",
            ),
        )


def test_reason_is_required():
    with pytest.raises(
        ValueError,
        match="Approval reason is required",
    ):
        apply_finops_approval(
            diff=_diff(),
            decision=FinOpsApprovalDecision(
                approved=True,
                reviewer="alice",
                reason="   ",
            ),
        )


def test_blank_cpu_override_is_rejected():
    with pytest.raises(
        ValueError,
        match="approved_cpu_request cannot be blank",
    ):
        apply_finops_approval(
            diff=_diff(),
            decision=FinOpsApprovalDecision(
                approved=True,
                reviewer="alice",
                reason="test",
                approved_cpu_request="   ",
            ),
        )


def test_blank_memory_override_is_rejected():
    with pytest.raises(
        ValueError,
        match="approved_memory_request cannot be blank",
    ):
        apply_finops_approval(
            diff=_diff(),
            decision=FinOpsApprovalDecision(
                approved=True,
                reviewer="alice",
                reason="test",
                approved_memory_request="   ",
            ),
        )


def test_approval_requires_at_least_one_resource_value():
    diff = GitOpsDiffProposal(
        namespace="default",
        workload_name="checkoutservice",
        workload_type="Deployment",
        target_file="manifest.yaml",
        manifest_kind="Deployment",
        manifest_name="checkoutservice",
        container_name="server",
        current_cpu_request="100m",
        proposed_cpu_request=None,
        current_memory_request="64Mi",
        proposed_memory_request=None,
        estimated_monthly_savings_usd=None,
        reason="test",
        confidence="low",
        requires_human_approval=True,
        writes_file=False,
        writes_git=False,
        auto_apply=False,
    )

    with pytest.raises(
        ValueError,
        match="at least one approved resource value",
    ):
        apply_finops_approval(
            diff=diff,
            decision=FinOpsApprovalDecision(
                approved=True,
                reviewer="alice",
                reason="approved",
            ),
        )
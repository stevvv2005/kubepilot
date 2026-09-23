from dataclasses import dataclass
from typing import Optional

from agent.finops_agent.gitops_diff import (
    GitOpsDiffProposal,
)


@dataclass(frozen=True)
class FinOpsApprovalDecision:
    approved: bool
    reviewer: str
    reason: str

    approved_cpu_request: Optional[str] = None
    approved_memory_request: Optional[str] = None


@dataclass(frozen=True)
class ApprovedFinOpsChange:
    namespace: str
    workload_name: str
    workload_type: str

    target_file: str
    manifest_kind: str
    manifest_name: str
    container_name: str

    current_cpu_request: Optional[str]
    proposed_cpu_request: Optional[str]
    approved_cpu_request: Optional[str]

    current_memory_request: Optional[str]
    proposed_memory_request: Optional[str]
    approved_memory_request: Optional[str]

    estimated_monthly_savings_usd: Optional[float]

    approved: bool
    reviewer: str
    reason: str

    ready_for_render: bool

    requires_human_approval: bool = True
    writes_file: bool = False
    writes_git: bool = False
    auto_apply: bool = False


def _validate_resource_value(
    value: Optional[str],
    field_name: str,
) -> None:
    if value is None:
        return

    if not isinstance(value, str):
        raise ValueError(
            f"{field_name} must be a string."
        )

    if not value.strip():
        raise ValueError(
            f"{field_name} cannot be blank."
        )


def apply_finops_approval(
    diff: GitOpsDiffProposal,
    decision: FinOpsApprovalDecision,
) -> ApprovedFinOpsChange:
    """
    Apply an explicit human approval decision to a
    read-only FinOps GitOps diff.

    This function does not modify any file, Git repository,
    Kubernetes resource, or cloud infrastructure.
    """

    reviewer = decision.reviewer.strip()

    if not reviewer:
        raise ValueError(
            "Reviewer is required."
        )

    reason = decision.reason.strip()

    if not reason:
        raise ValueError(
            "Approval reason is required."
        )

    _validate_resource_value(
        decision.approved_cpu_request,
        "approved_cpu_request",
    )

    _validate_resource_value(
        decision.approved_memory_request,
        "approved_memory_request",
    )

    if not decision.approved:
        return ApprovedFinOpsChange(
            namespace=diff.namespace,
            workload_name=diff.workload_name,
            workload_type=diff.workload_type,
            target_file=diff.target_file,
            manifest_kind=diff.manifest_kind,
            manifest_name=diff.manifest_name,
            container_name=diff.container_name,
            current_cpu_request=diff.current_cpu_request,
            proposed_cpu_request=diff.proposed_cpu_request,
            approved_cpu_request=None,
            current_memory_request=diff.current_memory_request,
            proposed_memory_request=diff.proposed_memory_request,
            approved_memory_request=None,
            estimated_monthly_savings_usd=(
                diff.estimated_monthly_savings_usd
            ),
            approved=False,
            reviewer=reviewer,
            reason=reason,
            ready_for_render=False,
            requires_human_approval=True,
            writes_file=False,
            writes_git=False,
            auto_apply=False,
        )

    approved_cpu = (
        decision.approved_cpu_request
        if decision.approved_cpu_request is not None
        else diff.proposed_cpu_request
    )

    approved_memory = (
        decision.approved_memory_request
        if decision.approved_memory_request is not None
        else diff.proposed_memory_request
    )

    if approved_cpu is None and approved_memory is None:
        raise ValueError(
            "Approved FinOps change must contain at least "
            "one approved resource value."
        )

    return ApprovedFinOpsChange(
        namespace=diff.namespace,
        workload_name=diff.workload_name,
        workload_type=diff.workload_type,
        target_file=diff.target_file,
        manifest_kind=diff.manifest_kind,
        manifest_name=diff.manifest_name,
        container_name=diff.container_name,
        current_cpu_request=diff.current_cpu_request,
        proposed_cpu_request=diff.proposed_cpu_request,
        approved_cpu_request=approved_cpu,
        current_memory_request=diff.current_memory_request,
        proposed_memory_request=diff.proposed_memory_request,
        approved_memory_request=approved_memory,
        estimated_monthly_savings_usd=(
            diff.estimated_monthly_savings_usd
        ),
        approved=True,
        reviewer=reviewer,
        reason=reason,
        ready_for_render=True,
        requires_human_approval=True,
        writes_file=False,
        writes_git=False,
        auto_apply=False,
    )
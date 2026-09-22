from dataclasses import dataclass
from typing import Optional

from agent.sre_agent.candidate_value import CandidateValue
from agent.sre_agent.patch_proposal import PatchProposal
from agent.sre_agent.reviewed_patch import (
    ReviewedPatchPayload,
    build_reviewed_patch_payload,
)


@dataclass(frozen=True)
class HumanApprovalDecision:
    approved: bool
    approved_value: Optional[str]
    reviewer: str
    reason: str


def apply_human_approval(
    patch_proposal: PatchProposal,
    candidate_value: CandidateValue,
    decision: HumanApprovalDecision,
) -> ReviewedPatchPayload:
    """
    Apply an explicit human approval decision to a remediation proposal.

    This function performs no file, Git, GitHub, or Kubernetes write.
    """

    if not decision.approved:
        return build_reviewed_patch_payload(
            patch_proposal=patch_proposal,
            candidate_value=candidate_value,
            approved_value=None,
        )

    if not decision.reviewer.strip():
        raise ValueError(
            "A reviewer identity is required for human approval."
        )

    if decision.approved_value is None:
        raise ValueError(
            "An approved value is required when approval is granted."
        )

    approved_value = decision.approved_value.strip()

    if not approved_value:
        raise ValueError(
            "Approved value cannot be empty."
        )

    return build_reviewed_patch_payload(
        patch_proposal=patch_proposal,
        candidate_value=candidate_value,
        approved_value=approved_value,
    )

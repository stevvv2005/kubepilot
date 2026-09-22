from dataclasses import dataclass
from typing import Optional

from agent.sre_agent.candidate_value import CandidateValue
from agent.sre_agent.patch_proposal import PatchProposal


@dataclass(frozen=True)
class ReviewedPatchPayload:
    incident_type: str
    target_file: Optional[str]
    container_name: Optional[str]
    field: str
    current_value: Optional[str]
    candidate_value: Optional[str]
    approved_value: Optional[str]
    reason: str
    confidence: str
    requires_human_approval: bool = True
    ready_for_pr: bool = False
    writes_file: bool = False
    auto_apply: bool = False


def build_reviewed_patch_payload(
    patch_proposal: PatchProposal,
    candidate_value: CandidateValue,
    approved_value: Optional[str] = None,
) -> ReviewedPatchPayload:
    """
    Build the final reviewed patch payload.

    A candidate value may be suggested automatically,
    but the payload is only ready for a Pull Request
    when an approved value is explicitly provided.

    This function never writes files and never modifies Kubernetes.
    """

    ready_for_pr = (
        approved_value is not None
        and patch_proposal.incident_type != "Healthy"
    )

    return ReviewedPatchPayload(
        incident_type=patch_proposal.incident_type,
        target_file=patch_proposal.target_file,
        container_name=patch_proposal.container_name,
        field=patch_proposal.field,
        current_value=patch_proposal.current_value,
        candidate_value=candidate_value.candidate_value,
        approved_value=approved_value,
        reason=candidate_value.reason,
        confidence=candidate_value.confidence,
        requires_human_approval=True,
        ready_for_pr=ready_for_pr,
        writes_file=False,
        auto_apply=False,
    )

from dataclasses import dataclass
from typing import Optional

from agent.sre_agent.manifest_diff import ManifestDiffProposal


@dataclass(frozen=True)
class PatchProposal:
    incident_type: str
    target_file: Optional[str]
    container_name: Optional[str]
    field: str
    current_value: Optional[str]
    proposed_value: Optional[str]
    reason: str
    requires_human_approval: bool = True
    writes_file: bool = False


def build_patch_proposal(
    manifest_diff: ManifestDiffProposal,
    container_name: Optional[str] = None,
    proposed_value: Optional[str] = None,
) -> PatchProposal:
    """
    Build a structured patch proposal.

    This function never writes to disk and never modifies Kubernetes.
    """

    if manifest_diff.incident_type == "ImagePullBackOff":
        return PatchProposal(
            incident_type="ImagePullBackOff",
            target_file=manifest_diff.target_file,
            container_name=container_name,
            field="image",
            current_value=manifest_diff.before,
            proposed_value=proposed_value,
            reason="Correct the invalid or unavailable container image.",
        )

    if manifest_diff.incident_type == "OOMKilled":
        return PatchProposal(
            incident_type="OOMKilled",
            target_file=manifest_diff.target_file,
            container_name=container_name,
            field="resources.limits.memory",
            current_value=manifest_diff.before,
            proposed_value=proposed_value,
            reason="Adjust the memory limit after reviewing observed usage.",
        )

    if manifest_diff.incident_type == "ReadinessProbeFailed":
        return PatchProposal(
            incident_type="ReadinessProbeFailed",
            target_file=manifest_diff.target_file,
            container_name=container_name,
            field="readinessProbe",
            current_value=manifest_diff.before,
            proposed_value=proposed_value,
            reason="Correct the readiness probe configuration.",
        )

    if manifest_diff.incident_type == "Healthy":
        return PatchProposal(
            incident_type="Healthy",
            target_file=None,
            container_name=None,
            field="none",
            current_value=None,
            proposed_value=None,
            reason="No patch is required.",
        )

    return PatchProposal(
        incident_type=manifest_diff.incident_type,
        target_file=manifest_diff.target_file,
        container_name=container_name,
        field="manual_review",
        current_value=manifest_diff.before,
        proposed_value=proposed_value,
        reason="Additional investigation is required before proposing a patch.",
    )

from dataclasses import dataclass
from typing import Optional

from agent.sre_agent.git_change import GitChangeProposal


@dataclass(frozen=True)
class ManifestDiffProposal:
    incident_type: str
    target_file: Optional[str]
    change_type: str
    before: Optional[str]
    after: Optional[str]
    requires_human_approval: bool = True
    writes_file: bool = False


def build_manifest_diff_proposal(
    git_change: GitChangeProposal,
) -> ManifestDiffProposal:
    """
    Build a safe manifest diff proposal.

    This function does not write files, commit Git changes,
    or modify Kubernetes resources.
    """

    if git_change.incident_type == "ImagePullBackOff":
        return ManifestDiffProposal(
            incident_type="ImagePullBackOff",
            target_file=git_change.target_file,
            change_type="update_container_image",
            before="image: invalid-or-missing-image",
            after="image: <validated-image>:<validated-tag>",
        )

    if git_change.incident_type == "OOMKilled":
        return ManifestDiffProposal(
            incident_type="OOMKilled",
            target_file=git_change.target_file,
            change_type="update_memory_limit",
            before="memory: <current-limit>",
            after="memory: <reviewed-new-limit>",
        )

    if git_change.incident_type == "ReadinessProbeFailed":
        return ManifestDiffProposal(
            incident_type="ReadinessProbeFailed",
            target_file=git_change.target_file,
            change_type="update_readiness_probe",
            before="readinessProbe: <current-configuration>",
            after="readinessProbe: <validated-configuration>",
        )

    if git_change.incident_type == "Healthy":
        return ManifestDiffProposal(
            incident_type="Healthy",
            target_file=None,
            change_type="none",
            before=None,
            after=None,
        )

    return ManifestDiffProposal(
        incident_type=git_change.incident_type,
        target_file=git_change.target_file,
        change_type="manual_review",
        before=None,
        after=None,
    )

from dataclasses import dataclass
from typing import Optional

from agent.sre_agent.remediation import RemediationProposal


@dataclass(frozen=True)
class GitChangeProposal:
    incident_type: str
    target_file: Optional[str]
    change_type: str
    description: str
    requires_human_approval: bool = True
    apply_directly: bool = False


def build_git_change_proposal(
    remediation: RemediationProposal,
) -> GitChangeProposal:
    """
    Convert a remediation proposal into a safe Git change proposal.

    This function does not modify files, Git repositories,
    or Kubernetes resources.
    """

    if remediation.incident_type == "ImagePullBackOff":
        return GitChangeProposal(
            incident_type="ImagePullBackOff",
            target_file=remediation.target_file,
            change_type="update_container_image",
            description=(
                "Prepare a Git change to correct the container image "
                "repository, tag, or imagePullSecrets."
            ),
        )

    if remediation.incident_type == "OOMKilled":
        return GitChangeProposal(
            incident_type="OOMKilled",
            target_file=remediation.target_file,
            change_type="update_memory_limit",
            description=(
                "Prepare a Git change to adjust the container memory limit "
                "after reviewing observed memory usage."
            ),
        )

    if remediation.incident_type == "ReadinessProbeFailed":
        return GitChangeProposal(
            incident_type="ReadinessProbeFailed",
            target_file=remediation.target_file,
            change_type="update_readiness_probe",
            description=(
                "Prepare a Git change to correct the readiness probe "
                "path, port, or timing configuration."
            ),
        )

    if remediation.incident_type == "Healthy":
        return GitChangeProposal(
            incident_type="Healthy",
            target_file=None,
            change_type="none",
            description="No Git change is required.",
        )

    return GitChangeProposal(
        incident_type=remediation.incident_type,
        target_file=remediation.target_file,
        change_type="manual_review",
        description=(
            "Additional investigation is required before preparing "
            "a Git change."
        ),
    )

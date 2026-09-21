from dataclasses import dataclass
from typing import Optional

from agent.sre_agent.diagnostic import Diagnosis


@dataclass(frozen=True)
class RemediationProposal:
    incident_type: str
    summary: str
    proposed_change: str
    target_file: Optional[str]
    requires_human_approval: bool = True
    direct_cluster_write: bool = False


def build_remediation_proposal(
    diagnosis: Diagnosis,
    target_file: Optional[str] = None,
) -> RemediationProposal:
    """
    Convert a diagnosis into a safe remediation proposal.

    This function never modifies Kubernetes directly.
    Any future change must go through Git + Pull Request.
    """

    if diagnosis.incident_type == "OOMKilled":
        return RemediationProposal(
            incident_type="OOMKilled",
            summary="Increase the container memory limit after reviewing usage.",
            proposed_change=(
                "Update the workload memory limit in Git based on observed "
                "memory usage and open a Pull Request for human review."
            ),
            target_file=target_file,
        )

    if diagnosis.incident_type == "ImagePullBackOff":
        return RemediationProposal(
            incident_type="ImagePullBackOff",
            summary="Correct the container image configuration.",
            proposed_change=(
                "Verify the image repository, tag, and imagePullSecrets. "
                "Update the Kubernetes manifest in Git and open a Pull Request."
            ),
            target_file=target_file,
        )

    if diagnosis.incident_type == "ReadinessProbeFailed":
        return RemediationProposal(
            incident_type="ReadinessProbeFailed",
            summary="Review and correct the readiness probe configuration.",
            proposed_change=(
                "Inspect the probe path, port, timing, and application behavior. "
                "Update the manifest in Git and open a Pull Request."
            ),
            target_file=target_file,
        )

    if diagnosis.incident_type == "Healthy":
        return RemediationProposal(
            incident_type="Healthy",
            summary="No remediation required.",
            proposed_change="No Git change is required.",
            target_file=None,
        )

    return RemediationProposal(
        incident_type=diagnosis.incident_type,
        summary="Manual investigation required.",
        proposed_change=(
            "Collect additional evidence before preparing any Git change."
        ),
        target_file=target_file,
    )

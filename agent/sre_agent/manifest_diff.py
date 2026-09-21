from dataclasses import dataclass
from typing import Optional

from agent.sre_agent.git_change import GitChangeProposal
from agent.sre_agent.manifest_state import get_container_manifest_state


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
    container_name: Optional[str] = None,
) -> ManifestDiffProposal:
    """
    Build a safe manifest diff proposal.

    This function may read the target manifest,
    but it never writes files, commits changes,
    or modifies Kubernetes resources.
    """

    if git_change.incident_type == "ImagePullBackOff":
        before = "image: <unknown>"

        if git_change.target_file and container_name:
            state = get_container_manifest_state(
                manifest_path=git_change.target_file,
                container_name=container_name,
            )

            if state.image:
                before = f"image: {state.image}"

        return ManifestDiffProposal(
            incident_type="ImagePullBackOff",
            target_file=git_change.target_file,
            change_type="update_container_image",
            before=before,
            after="image: <validated-image>:<validated-tag>",
        )

    if git_change.incident_type == "OOMKilled":
        before = "memory: <unknown>"

        if git_change.target_file and container_name:
            state = get_container_manifest_state(
                manifest_path=git_change.target_file,
                container_name=container_name,
            )

            if state.memory_limit:
                before = f"memory: {state.memory_limit}"

        return ManifestDiffProposal(
            incident_type="OOMKilled",
            target_file=git_change.target_file,
            change_type="update_memory_limit",
            before=before,
            after="memory: <reviewed-new-limit>",
        )

    if git_change.incident_type == "ReadinessProbeFailed":
        before = "readinessProbe: <unknown>"

        if git_change.target_file and container_name:
            state = get_container_manifest_state(
                manifest_path=git_change.target_file,
                container_name=container_name,
            )

            if state.readiness_path is not None or state.readiness_port is not None:
                before = (
                    "readinessProbe: "
                    f"path={state.readiness_path}, "
                    f"port={state.readiness_port}"
                )

        return ManifestDiffProposal(
            incident_type="ReadinessProbeFailed",
            target_file=git_change.target_file,
            change_type="update_readiness_probe",
            before=before,
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

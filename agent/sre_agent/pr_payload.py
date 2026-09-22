from dataclasses import dataclass
from typing import Optional

from agent.sre_agent.reviewed_patch import ReviewedPatchPayload


@dataclass(frozen=True)
class PullRequestPayload:
    incident_type: str
    title: str
    branch_name: str
    target_file: Optional[str]
    container_name: Optional[str]
    field: str
    current_value: Optional[str]
    approved_value: Optional[str]
    commit_message: str
    pr_body: str
    ready_to_create: bool
    writes_git: bool = False
    creates_pr: bool = False


def build_pr_payload(
    reviewed_patch: ReviewedPatchPayload,
) -> PullRequestPayload:
    """
    Build a reviewable Pull Request payload.

    This function only prepares PR metadata.
    It does not modify Git, write files, or create a Pull Request.
    """

    incident = reviewed_patch.incident_type

    if not reviewed_patch.ready_for_pr:
        return PullRequestPayload(
            incident_type=incident,
            title=f"fix(sre): review {incident} remediation",
            branch_name=f"fix/sre-{incident.lower()}-pending",
            target_file=reviewed_patch.target_file,
            container_name=reviewed_patch.container_name,
            field=reviewed_patch.field,
            current_value=reviewed_patch.current_value,
            approved_value=reviewed_patch.approved_value,
            commit_message=f"fix(sre): review {incident} remediation",
            pr_body=(
                "This remediation is not ready for Pull Request creation. "
                "Human approval is still required."
            ),
            ready_to_create=False,
        )

    title = f"fix(sre): remediate {incident}"
    branch_name = f"fix/sre-{incident.lower()}"
    commit_message = f"fix(sre): remediate {incident}"

    pr_body = (
        "## KubePilot SRE Remediation\n\n"
        f"- Incident: `{incident}`\n"
        f"- Target file: `{reviewed_patch.target_file}`\n"
        f"- Container: `{reviewed_patch.container_name}`\n"
        f"- Field: `{reviewed_patch.field}`\n"
        f"- Current value: `{reviewed_patch.current_value}`\n"
        f"- Approved value: `{reviewed_patch.approved_value}`\n"
        f"- Confidence: `{reviewed_patch.confidence}`\n\n"
        "## Safety\n\n"
        "- Human approval was provided\n"
        "- No direct Kubernetes write is performed\n"
        "- Deployment remains managed through GitOps / ArgoCD\n"
    )

    return PullRequestPayload(
        incident_type=incident,
        title=title,
        branch_name=branch_name,
        target_file=reviewed_patch.target_file,
        container_name=reviewed_patch.container_name,
        field=reviewed_patch.field,
        current_value=reviewed_patch.current_value,
        approved_value=reviewed_patch.approved_value,
        commit_message=commit_message,
        pr_body=pr_body,
        ready_to_create=True,
    )

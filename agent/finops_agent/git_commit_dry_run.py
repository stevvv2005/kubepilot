from dataclasses import dataclass

from agent.finops_agent.approved_manifest import (
    ApprovedFinOpsManifest,
)


@dataclass(frozen=True)
class FinOpsGitCommitDryRun:
    target_file: str
    branch_name: str
    commit_message: str
    rendered_yaml: str

    ready_to_commit: bool

    performs_write: bool = False
    writes_file: bool = False
    writes_git: bool = False


def _build_branch_name(
    manifest_name: str,
) -> str:
    """
    Build a deterministic FinOps branch name.
    """

    normalized = (
        manifest_name
        .strip()
        .lower()
        .replace("_", "-")
        .replace(" ", "-")
    )

    if not normalized:
        raise ValueError(
            "Manifest name is required to build branch name."
        )

    return (
        f"fix/finops-{normalized}-rightsizing"
    )


def _build_commit_message(
    manifest_name: str,
) -> str:
    """
    Build a deterministic FinOps commit message.
    """

    normalized = manifest_name.strip()

    if not normalized:
        raise ValueError(
            "Manifest name is required to build commit message."
        )

    return (
        f"fix(finops): rightsize {normalized}"
    )


def build_finops_git_commit_dry_run(
    approved_manifest: ApprovedFinOpsManifest,
) -> FinOpsGitCommitDryRun:
    """
    Build a Git commit plan for an approved FinOps manifest.

    No file or Git write is performed.
    """

    if not approved_manifest.ready_for_commit:
        raise ValueError(
            "Approved FinOps manifest is not ready for commit."
        )

    if approved_manifest.writes_file:
        raise ValueError(
            "Approved FinOps manifest must not write files."
        )

    if approved_manifest.writes_git:
        raise ValueError(
            "Approved FinOps manifest must not write Git."
        )

    if not approved_manifest.target_file.strip():
        raise ValueError(
            "Target file is required."
        )

    if not approved_manifest.rendered_yaml.strip():
        raise ValueError(
            "Rendered YAML is required."
        )

    branch_name = _build_branch_name(
        approved_manifest.manifest_name,
    )

    commit_message = _build_commit_message(
        approved_manifest.manifest_name,
    )

    return FinOpsGitCommitDryRun(
        target_file=approved_manifest.target_file,
        branch_name=branch_name,
        commit_message=commit_message,
        rendered_yaml=approved_manifest.rendered_yaml,
        ready_to_commit=True,
        performs_write=False,
        writes_file=False,
        writes_git=False,
    )
from dataclasses import dataclass

from agent.sre_agent.approved_manifest import ApprovedManifestRender
from agent.sre_agent.pr_payload import PullRequestPayload


@dataclass(frozen=True)
class GitCommitDryRun:
    target_file: str
    branch_name: str
    commit_message: str
    rendered_yaml: str
    ready_to_commit: bool
    performs_write: bool = False
    writes_file: bool = False
    writes_git: bool = False


def build_git_commit_dry_run(
    approved_manifest: ApprovedManifestRender,
    pr_payload: PullRequestPayload,
) -> GitCommitDryRun:
    """
    Build a Git commit plan without writing anything.

    This function performs no file write, no Git command,
    and no GitHub operation.
    """

    if not approved_manifest.ready_for_commit:
        raise ValueError(
            "Approved manifest is not ready for commit."
        )

    if not pr_payload.ready_to_create:
        raise ValueError(
            "Pull Request payload is not ready for commit preparation."
        )

    if approved_manifest.target_file != pr_payload.target_file:
        raise ValueError(
            "Approved manifest target file does not match PR payload."
        )

    if not pr_payload.branch_name.strip():
        raise ValueError(
            "A Git branch name is required."
        )

    if not pr_payload.commit_message.strip():
        raise ValueError(
            "A commit message is required."
        )

    return GitCommitDryRun(
        target_file=approved_manifest.target_file,
        branch_name=pr_payload.branch_name,
        commit_message=pr_payload.commit_message,
        rendered_yaml=approved_manifest.rendered_yaml,
        ready_to_commit=True,
        performs_write=False,
        writes_file=False,
        writes_git=False,
    )

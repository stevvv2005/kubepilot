import pytest

from agent.sre_agent.approved_manifest import ApprovedManifestRender
from agent.sre_agent.git_commit_dry_run import (
    build_git_commit_dry_run,
)
from agent.sre_agent.pr_payload import PullRequestPayload


def build_manifest(
    target_file: str = "chaos/oomkilled-pod.yaml",
    ready_for_commit: bool = True,
) -> ApprovedManifestRender:
    return ApprovedManifestRender(
        target_file=target_file,
        container_name="memory-hog",
        field="resources.limits.memory",
        approved_value="64Mi",
        rendered_yaml=(
            "apiVersion: v1\n"
            "kind: Pod\n"
            "metadata:\n"
            "  name: kubepilot-oomkilled\n"
            "spec:\n"
            "  containers:\n"
            "  - name: memory-hog\n"
            "    resources:\n"
            "      limits:\n"
            "        memory: 64Mi\n"
        ),
        ready_for_commit=ready_for_commit,
        writes_file=False,
        writes_git=False,
    )


def build_pr_payload(
    target_file: str = "chaos/oomkilled-pod.yaml",
    ready_to_create: bool = True,
) -> PullRequestPayload:
    return PullRequestPayload(
        incident_type="OOMKilled",
        title="fix(sre): remediate OOMKilled",
        branch_name="fix/sre-oomkilled",
        target_file=target_file,
        container_name="memory-hog",
        field="resources.limits.memory",
        current_value="memory: 32Mi",
        approved_value="64Mi",
        commit_message="fix(sre): remediate OOMKilled",
        pr_body="Approved remediation.",
        ready_to_create=ready_to_create,
        writes_git=False,
        creates_pr=False,
    )


def test_build_git_commit_dry_run():
    result = build_git_commit_dry_run(
        approved_manifest=build_manifest(),
        pr_payload=build_pr_payload(),
    )

    assert result.target_file == "chaos/oomkilled-pod.yaml"
    assert result.branch_name == "fix/sre-oomkilled"
    assert result.commit_message == (
        "fix(sre): remediate OOMKilled"
    )
    assert "memory: 64Mi" in result.rendered_yaml

    assert result.ready_to_commit is True
    assert result.performs_write is False
    assert result.writes_file is False
    assert result.writes_git is False


def test_manifest_must_be_ready():
    with pytest.raises(
        ValueError,
        match="not ready for commit",
    ):
        build_git_commit_dry_run(
            approved_manifest=build_manifest(
                ready_for_commit=False,
            ),
            pr_payload=build_pr_payload(),
        )


def test_pr_payload_must_be_ready():
    with pytest.raises(
        ValueError,
        match="not ready for commit preparation",
    ):
        build_git_commit_dry_run(
            approved_manifest=build_manifest(),
            pr_payload=build_pr_payload(
                ready_to_create=False,
            ),
        )


def test_target_files_must_match():
    with pytest.raises(
        ValueError,
        match="target file does not match",
    ):
        build_git_commit_dry_run(
            approved_manifest=build_manifest(
                target_file="chaos/oomkilled-pod.yaml",
            ),
            pr_payload=build_pr_payload(
                target_file="chaos/other.yaml",
            ),
        )


def test_dry_run_never_performs_writes():
    result = build_git_commit_dry_run(
        approved_manifest=build_manifest(),
        pr_payload=build_pr_payload(),
    )

    assert result.performs_write is False
    assert result.writes_file is False
    assert result.writes_git is False

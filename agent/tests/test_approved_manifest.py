from pathlib import Path

import pytest
import yaml

from agent.sre_agent.approved_manifest import (
    render_approved_manifest,
)
from agent.sre_agent.reviewed_patch import (
    ReviewedPatchPayload,
)


TARGET_FILE = "chaos/oomkilled-pod.yaml"


def build_reviewed_patch(
    approved_value: str | None = "64Mi",
    ready_for_pr: bool = True,
    target_file: str = TARGET_FILE,
    field: str = "resources.limits.memory",
) -> ReviewedPatchPayload:
    return ReviewedPatchPayload(
        incident_type="OOMKilled",
        target_file=target_file,
        container_name="memory-hog",
        field=field,
        current_value="memory: 32Mi",
        candidate_value="64Mi",
        approved_value=approved_value,
        reason="Human-reviewed memory increase.",
        confidence="medium",
        requires_human_approval=True,
        ready_for_pr=ready_for_pr,
        writes_file=False,
        auto_apply=False,
    )


def create_test_manifest(
    repository_root: Path,
) -> Path:
    chaos_dir = repository_root / "chaos"

    chaos_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    manifest_path = (
        chaos_dir / "oomkilled-pod.yaml"
    )

    manifest_path.write_text(
        """
apiVersion: v1
kind: Pod
metadata:
  name: kubepilot-oomkilled
spec:
  containers:
    - name: memory-hog
      image: python:3.14-alpine
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
        limits:
          cpu: 100m
          memory: 32Mi
""".strip()
        + "\n",
        encoding="utf-8",
    )

    return manifest_path


def test_render_approved_memory_limit_in_memory(
    tmp_path,
):
    create_test_manifest(tmp_path)

    reviewed_patch = build_reviewed_patch()

    result = render_approved_manifest(
        reviewed_patch=reviewed_patch,
        repository_root=tmp_path,
    )

    rendered = yaml.safe_load(
        result.rendered_yaml,
    )

    container = (
        rendered["spec"]["containers"][0]
    )

    assert container["name"] == "memory-hog"

    assert (
        container["resources"]
        ["limits"]
        ["memory"]
        == "64Mi"
    )

    assert result.target_file == TARGET_FILE
    assert result.approved_value == "64Mi"
    assert result.ready_for_commit is True
    assert result.writes_file is False
    assert result.writes_git is False


def test_renderer_does_not_modify_original_file(
    tmp_path,
):
    manifest_path = create_test_manifest(
        tmp_path,
    )

    original_content = (
        manifest_path.read_text(
            encoding="utf-8",
        )
    )

    reviewed_patch = build_reviewed_patch()

    render_approved_manifest(
        reviewed_patch=reviewed_patch,
        repository_root=tmp_path,
    )

    content_after_render = (
        manifest_path.read_text(
            encoding="utf-8",
        )
    )

    assert (
        content_after_render
        == original_content
    )

    assert "memory: 32Mi" in original_content


def test_unapproved_patch_cannot_be_rendered(
    tmp_path,
):
    create_test_manifest(tmp_path)

    reviewed_patch = build_reviewed_patch(
        approved_value=None,
        ready_for_pr=False,
    )

    with pytest.raises(
        ValueError,
        match="not approved",
    ):
        render_approved_manifest(
            reviewed_patch=reviewed_patch,
            repository_root=tmp_path,
        )


def test_unsupported_field_is_rejected(
    tmp_path,
):
    create_test_manifest(tmp_path)

    reviewed_patch = build_reviewed_patch(
        field="unsupported.field",
    )

    with pytest.raises(
        ValueError,
        match="Unsupported approved field",
    ):
        render_approved_manifest(
            reviewed_patch=reviewed_patch,
            repository_root=tmp_path,
        )


def test_parent_traversal_is_rejected(
    tmp_path,
):
    reviewed_patch = build_reviewed_patch(
        target_file="../secret.yaml",
    )

    with pytest.raises(
        ValueError,
        match="Unsafe target file path",
    ):
        render_approved_manifest(
            reviewed_patch=reviewed_patch,
            repository_root=tmp_path,
        )


def test_absolute_target_is_rejected(
    tmp_path,
):
    absolute_target = str(
        tmp_path / "secret.yaml"
    )

    reviewed_patch = build_reviewed_patch(
        target_file=absolute_target,
    )

    with pytest.raises(
        ValueError,
        match="repository-relative",
    ):
        render_approved_manifest(
            reviewed_patch=reviewed_patch,
            repository_root=tmp_path,
        )

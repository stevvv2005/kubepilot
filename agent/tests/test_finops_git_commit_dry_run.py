import pytest

from agent.finops_agent.approved_manifest import (
    ApprovedFinOpsManifest,
)
from agent.finops_agent.git_commit_dry_run import (
    _build_branch_name,
    _build_commit_message,
    build_finops_git_commit_dry_run,
)


def _approved_manifest() -> ApprovedFinOpsManifest:
    return ApprovedFinOpsManifest(
        target_file=(
            "gitops/apps/online-boutique/base/"
            "kubernetes-manifests.yaml"
        ),
        manifest_kind="Deployment",
        manifest_name="checkoutservice",
        container_name="server",
        approved_cpu_request="50m",
        approved_memory_request="32Mi",
        rendered_yaml=(
            "apiVersion: apps/v1\n"
            "kind: Deployment\n"
            "metadata:\n"
            "  name: checkoutservice\n"
        ),
        ready_for_commit=True,
        writes_file=False,
        writes_git=False,
    )


def test_build_finops_git_commit_dry_run():
    result = build_finops_git_commit_dry_run(
        _approved_manifest(),
    )

    assert (
        result.target_file
        == (
            "gitops/apps/online-boutique/base/"
            "kubernetes-manifests.yaml"
        )
    )

    assert (
        result.branch_name
        == "fix/finops-checkoutservice-rightsizing"
    )

    assert (
        result.commit_message
        == "fix(finops): rightsize checkoutservice"
    )

    assert "checkoutservice" in result.rendered_yaml

    assert result.ready_to_commit is True
    assert result.performs_write is False
    assert result.writes_file is False
    assert result.writes_git is False


def test_branch_name_builder():
    assert (
        _build_branch_name(
            "checkoutservice"
        )
        == "fix/finops-checkoutservice-rightsizing"
    )

    assert (
        _build_branch_name(
            "redis-cart"
        )
        == "fix/finops-redis-cart-rightsizing"
    )


def test_branch_name_normalizes_spaces_and_underscores():
    assert (
        _build_branch_name(
            "My_Service Name"
        )
        == "fix/finops-my-service-name-rightsizing"
    )


def test_commit_message_builder():
    assert (
        _build_commit_message(
            "checkoutservice"
        )
        == "fix(finops): rightsize checkoutservice"
    )


def test_not_ready_manifest_is_rejected():
    manifest = _approved_manifest()

    invalid = ApprovedFinOpsManifest(
        target_file=manifest.target_file,
        manifest_kind=manifest.manifest_kind,
        manifest_name=manifest.manifest_name,
        container_name=manifest.container_name,
        approved_cpu_request=manifest.approved_cpu_request,
        approved_memory_request=manifest.approved_memory_request,
        rendered_yaml=manifest.rendered_yaml,
        ready_for_commit=False,
        writes_file=False,
        writes_git=False,
    )

    with pytest.raises(
        ValueError,
        match="not ready for commit",
    ):
        build_finops_git_commit_dry_run(
            invalid,
        )


def test_manifest_with_file_write_flag_is_rejected():
    manifest = _approved_manifest()

    invalid = ApprovedFinOpsManifest(
        target_file=manifest.target_file,
        manifest_kind=manifest.manifest_kind,
        manifest_name=manifest.manifest_name,
        container_name=manifest.container_name,
        approved_cpu_request=manifest.approved_cpu_request,
        approved_memory_request=manifest.approved_memory_request,
        rendered_yaml=manifest.rendered_yaml,
        ready_for_commit=True,
        writes_file=True,
        writes_git=False,
    )

    with pytest.raises(
        ValueError,
        match="must not write files",
    ):
        build_finops_git_commit_dry_run(
            invalid,
        )


def test_manifest_with_git_write_flag_is_rejected():
    manifest = _approved_manifest()

    invalid = ApprovedFinOpsManifest(
        target_file=manifest.target_file,
        manifest_kind=manifest.manifest_kind,
        manifest_name=manifest.manifest_name,
        container_name=manifest.container_name,
        approved_cpu_request=manifest.approved_cpu_request,
        approved_memory_request=manifest.approved_memory_request,
        rendered_yaml=manifest.rendered_yaml,
        ready_for_commit=True,
        writes_file=False,
        writes_git=True,
    )

    with pytest.raises(
        ValueError,
        match="must not write Git",
    ):
        build_finops_git_commit_dry_run(
            invalid,
        )


def test_empty_target_file_is_rejected():
    manifest = _approved_manifest()

    invalid = ApprovedFinOpsManifest(
        target_file="   ",
        manifest_kind=manifest.manifest_kind,
        manifest_name=manifest.manifest_name,
        container_name=manifest.container_name,
        approved_cpu_request=manifest.approved_cpu_request,
        approved_memory_request=manifest.approved_memory_request,
        rendered_yaml=manifest.rendered_yaml,
        ready_for_commit=True,
        writes_file=False,
        writes_git=False,
    )

    with pytest.raises(
        ValueError,
        match="Target file is required",
    ):
        build_finops_git_commit_dry_run(
            invalid,
        )


def test_empty_rendered_yaml_is_rejected():
    manifest = _approved_manifest()

    invalid = ApprovedFinOpsManifest(
        target_file=manifest.target_file,
        manifest_kind=manifest.manifest_kind,
        manifest_name=manifest.manifest_name,
        container_name=manifest.container_name,
        approved_cpu_request=manifest.approved_cpu_request,
        approved_memory_request=manifest.approved_memory_request,
        rendered_yaml="   ",
        ready_for_commit=True,
        writes_file=False,
        writes_git=False,
    )

    with pytest.raises(
        ValueError,
        match="Rendered YAML is required",
    ):
        build_finops_git_commit_dry_run(
            invalid,
        )


def test_blank_manifest_name_is_rejected_for_branch():
    with pytest.raises(
        ValueError,
        match="Manifest name is required",
    ):
        _build_branch_name(
            "   ",
        )


def test_blank_manifest_name_is_rejected_for_commit_message():
    with pytest.raises(
        ValueError,
        match="Manifest name is required",
    ):
        _build_commit_message(
            "   ",
        )
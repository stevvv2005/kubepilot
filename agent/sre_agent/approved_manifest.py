from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml

from agent.sre_agent.manifest_reader import read_manifest
from agent.sre_agent.reviewed_patch import ReviewedPatchPayload


@dataclass(frozen=True)
class ApprovedManifestRender:
    target_file: str
    container_name: str
    field: str
    approved_value: str
    rendered_yaml: str
    ready_for_commit: bool
    writes_file: bool = False
    writes_git: bool = False


def _get_pod_spec(
    manifest: Dict[str, Any],
) -> Dict[str, Any]:
    kind = manifest.get("kind")

    if kind == "Pod":
        spec = manifest.get("spec")

    elif kind in {
        "Deployment",
        "StatefulSet",
        "DaemonSet",
    }:
        spec = (
            manifest
            .get("spec", {})
            .get("template", {})
            .get("spec")
        )

    else:
        raise ValueError(
            "Unsupported Kubernetes kind "
            f"for manifest rendering: {kind}"
        )

    if not isinstance(spec, dict):
        raise ValueError(
            "Unable to locate Kubernetes pod spec in manifest."
        )

    return spec


def _find_container(
    pod_spec: Dict[str, Any],
    container_name: str,
) -> Dict[str, Any]:
    containers = pod_spec.get("containers")

    if not isinstance(containers, list):
        raise ValueError(
            "Manifest does not contain a valid containers list."
        )

    for container in containers:
        if (
            isinstance(container, dict)
            and container.get("name") == container_name
        ):
            return container

    raise ValueError(
        f"Container '{container_name}' "
        "was not found in the manifest."
    )


def _resolve_safe_target(
    repository_root: Path,
    target_file: str,
) -> Path:
    """
    Resolve a repository-relative target file safely.

    Absolute paths and parent-directory traversal are rejected.
    The final resolved path must remain inside repository_root.
    """

    relative_target = Path(target_file)

    if relative_target.is_absolute():
        raise ValueError(
            "Target file must be repository-relative."
        )

    if ".." in relative_target.parts:
        raise ValueError(
            "Unsafe target file path."
        )

    root = repository_root.resolve()

    resolved_target = (
        root / relative_target
    ).resolve()

    if not resolved_target.is_relative_to(root):
        raise ValueError(
            "Target file escapes the repository root."
        )

    return resolved_target


def render_approved_manifest(
    reviewed_patch: ReviewedPatchPayload,
    repository_root: str | Path = ".",
) -> ApprovedManifestRender:
    """
    Render an approved Kubernetes manifest in memory.

    The approved target file must be relative to repository_root.

    This function:
    - reads the existing manifest
    - creates an in-memory copy
    - applies the human-approved value
    - serializes the modified manifest to YAML
    - performs no file write
    - performs no Git operation
    """

    if not reviewed_patch.ready_for_pr:
        raise ValueError(
            "Reviewed patch is not approved and ready for PR."
        )

    if reviewed_patch.target_file is None:
        raise ValueError(
            "A target file is required."
        )

    if reviewed_patch.container_name is None:
        raise ValueError(
            "A container name is required."
        )

    if reviewed_patch.approved_value is None:
        raise ValueError(
            "An approved value is required."
        )

    approved_value = (
        reviewed_patch.approved_value.strip()
    )

    if not approved_value:
        raise ValueError(
            "Approved value cannot be empty."
        )

    resolved_target = _resolve_safe_target(
        repository_root=Path(repository_root),
        target_file=reviewed_patch.target_file,
    )

    manifest = read_manifest(
        str(resolved_target),
    )

    rendered_manifest = deepcopy(
        manifest,
    )

    pod_spec = _get_pod_spec(
        rendered_manifest,
    )

    container = _find_container(
        pod_spec=pod_spec,
        container_name=reviewed_patch.container_name,
    )

    if (
        reviewed_patch.field
        == "resources.limits.memory"
    ):
        resources = container.setdefault(
            "resources",
            {},
        )

        limits = resources.setdefault(
            "limits",
            {},
        )

        limits["memory"] = approved_value

    else:
        raise ValueError(
            "Unsupported approved field: "
            f"{reviewed_patch.field}"
        )

    rendered_yaml = yaml.safe_dump(
        rendered_manifest,
        sort_keys=False,
        default_flow_style=False,
    )

    return ApprovedManifestRender(
        target_file=reviewed_patch.target_file,
        container_name=reviewed_patch.container_name,
        field=reviewed_patch.field,
        approved_value=approved_value,
        rendered_yaml=rendered_yaml,
        ready_for_commit=True,
        writes_file=False,
        writes_git=False,
    )

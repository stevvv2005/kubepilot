from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

from agent.finops_agent.target_file_resolver import (
    FinOpsTargetResolution,
)


@dataclass(frozen=True)
class FinOpsManifestState:
    target_file: str

    manifest_kind: str
    manifest_name: str

    container_name: str

    cpu_request: Optional[str]
    memory_request: Optional[str]

    cpu_limit: Optional[str]
    memory_limit: Optional[str]

    found: bool
    reason: str

    read_only: bool = True
    performs_write: bool = False


def _resolve_repository_file(
    repository_root: str,
    target_file: str,
) -> Path:
    """
    Resolve a repository-relative target safely.

    The resolved path must remain inside repository_root.
    """

    root = Path(
        repository_root,
    ).resolve()

    target = (
        root
        / target_file
    ).resolve()

    try:
        target.relative_to(
            root,
        )
    except ValueError as exc:
        raise ValueError(
            "Target file escapes repository root."
        ) from exc

    return target


def _find_manifest_document(
    documents: list,
    kind: str,
    name: str,
) -> Optional[dict]:
    """
    Find one Kubernetes object in a multi-document YAML file.
    """

    for document in documents:
        if not isinstance(
            document,
            dict,
        ):
            continue

        if document.get("kind") != kind:
            continue

        metadata = document.get(
            "metadata",
            {},
        )

        if not isinstance(
            metadata,
            dict,
        ):
            continue

        if metadata.get("name") == name:
            return document

    return None


def _get_pod_spec(
    document: dict,
) -> Optional[dict]:
    """
    Extract the pod spec from supported workload kinds.
    """

    kind = document.get("kind")

    if kind in {
        "Deployment",
        "StatefulSet",
        "DaemonSet",
    }:
        spec = document.get(
            "spec",
            {},
        )

        template = spec.get(
            "template",
            {},
        )

        pod_spec = template.get(
            "spec",
            {},
        )

        if isinstance(
            pod_spec,
            dict,
        ):
            return pod_spec

    if kind == "Pod":
        pod_spec = document.get(
            "spec",
            {},
        )

        if isinstance(
            pod_spec,
            dict,
        ):
            return pod_spec

    return None


def _read_resource_value(
    resources: dict,
    section: str,
    resource_name: str,
) -> Optional[str]:
    section_data = resources.get(
        section,
        {},
    )

    if not isinstance(
        section_data,
        dict,
    ):
        return None

    value = section_data.get(
        resource_name,
    )

    if value is None:
        return None

    return str(
        value,
    )


def inspect_finops_manifest(
    resolution: FinOpsTargetResolution,
    repository_root: str = ".",
) -> FinOpsManifestState:
    """
    Read the allowlisted GitOps manifest and extract
    the current resource configuration.

    This function is strictly read-only.
    """

    if not resolution.matched:
        raise ValueError(
            "Cannot inspect an unresolved FinOps target."
        )

    if not resolution.target_file:
        raise ValueError(
            "Resolved FinOps target has no target file."
        )

    if not resolution.manifest_kind:
        raise ValueError(
            "Resolved FinOps target has no manifest kind."
        )

    if not resolution.manifest_name:
        raise ValueError(
            "Resolved FinOps target has no manifest name."
        )

    target_path = _resolve_repository_file(
        repository_root=repository_root,
        target_file=resolution.target_file,
    )

    if not target_path.is_file():
        raise ValueError(
            f"GitOps target file does not exist: "
            f"{resolution.target_file}"
        )

    with target_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        documents = list(
            yaml.safe_load_all(
                file,
            )
        )

    document = _find_manifest_document(
        documents=documents,
        kind=resolution.manifest_kind,
        name=resolution.manifest_name,
    )

    if document is None:
        return FinOpsManifestState(
            target_file=resolution.target_file,
            manifest_kind=resolution.manifest_kind,
            manifest_name=resolution.manifest_name,
            container_name="",
            cpu_request=None,
            memory_request=None,
            cpu_limit=None,
            memory_limit=None,
            found=False,
            reason=(
                "Allowlisted Kubernetes manifest "
                "was not found in the target file."
            ),
            read_only=True,
            performs_write=False,
        )

    pod_spec = _get_pod_spec(
        document,
    )

    if pod_spec is None:
        return FinOpsManifestState(
            target_file=resolution.target_file,
            manifest_kind=resolution.manifest_kind,
            manifest_name=resolution.manifest_name,
            container_name="",
            cpu_request=None,
            memory_request=None,
            cpu_limit=None,
            memory_limit=None,
            found=False,
            reason=(
                "Kubernetes manifest does not contain "
                "a supported pod specification."
            ),
            read_only=True,
            performs_write=False,
        )

    containers = pod_spec.get(
        "containers",
        [],
    )

    if not isinstance(
        containers,
        list,
    ):
        containers = []

    if not containers:
        return FinOpsManifestState(
            target_file=resolution.target_file,
            manifest_kind=resolution.manifest_kind,
            manifest_name=resolution.manifest_name,
            container_name="",
            cpu_request=None,
            memory_request=None,
            cpu_limit=None,
            memory_limit=None,
            found=False,
            reason=(
                "Kubernetes manifest contains no containers."
            ),
            read_only=True,
            performs_write=False,
        )

    if len(containers) != 1:
        return FinOpsManifestState(
            target_file=resolution.target_file,
            manifest_kind=resolution.manifest_kind,
            manifest_name=resolution.manifest_name,
            container_name="",
            cpu_request=None,
            memory_request=None,
            cpu_limit=None,
            memory_limit=None,
            found=False,
            reason=(
                "Manifest contains multiple containers. "
                "Automatic container selection is disabled."
            ),
            read_only=True,
            performs_write=False,
        )

    container = containers[0]

    if not isinstance(
        container,
        dict,
    ):
        raise ValueError(
            "Container definition must be a mapping."
        )

    container_name = str(
        container.get(
            "name",
            "",
        )
    )

    if not container_name:
        raise ValueError(
            "Container definition has no name."
        )

    resources = container.get(
        "resources",
        {},
    )

    if not isinstance(
        resources,
        dict,
    ):
        resources = {}

    return FinOpsManifestState(
        target_file=resolution.target_file,
        manifest_kind=resolution.manifest_kind,
        manifest_name=resolution.manifest_name,
        container_name=container_name,
        cpu_request=_read_resource_value(
            resources,
            "requests",
            "cpu",
        ),
        memory_request=_read_resource_value(
            resources,
            "requests",
            "memory",
        ),
        cpu_limit=_read_resource_value(
            resources,
            "limits",
            "cpu",
        ),
        memory_limit=_read_resource_value(
            resources,
            "limits",
            "memory",
        ),
        found=True,
        reason=(
            "Current GitOps resource configuration "
            "was read successfully."
        ),
        read_only=True,
        performs_write=False,
    )

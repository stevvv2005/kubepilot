from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

import yaml

from agent.finops_agent.human_approval import (
    ApprovedFinOpsChange,
)


@dataclass(frozen=True)
class ApprovedFinOpsManifest:
    target_file: str

    manifest_kind: str
    manifest_name: str
    container_name: str

    approved_cpu_request: str | None
    approved_memory_request: str | None

    rendered_yaml: str

    ready_for_commit: bool

    writes_file: bool = False
    writes_git: bool = False


def _resolve_repository_file(
    repository_root: str,
    target_file: str,
) -> Path:
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
) -> dict:
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

    raise ValueError(
        "Approved FinOps manifest target was not found."
    )


def _get_pod_spec(
    document: dict,
) -> dict:
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

    raise ValueError(
        "Unsupported Kubernetes workload structure."
    )


def _find_container(
    pod_spec: dict,
    container_name: str,
) -> dict:
    containers = pod_spec.get(
        "containers",
        [],
    )

    if not isinstance(
        containers,
        list,
    ):
        raise ValueError(
            "Kubernetes containers field must be a list."
        )

    for container in containers:
        if not isinstance(
            container,
            dict,
        ):
            continue

        if (
            container.get("name")
            == container_name
        ):
            return container

    raise ValueError(
        "Approved FinOps container was not found."
    )


def render_approved_finops_manifest(
    approved_change: ApprovedFinOpsChange,
    repository_root: str = ".",
) -> ApprovedFinOpsManifest:
    """
    Render an approved FinOps resource change in memory.

    No file or Git write is performed.
    """

    if not approved_change.approved:
        raise ValueError(
            "FinOps change must be explicitly approved."
        )

    if not approved_change.ready_for_render:
        raise ValueError(
            "Approved FinOps change is not ready for rendering."
        )

    if (
        approved_change.approved_cpu_request is None
        and approved_change.approved_memory_request is None
    ):
        raise ValueError(
            "At least one approved resource request is required."
        )

    target_path = _resolve_repository_file(
        repository_root=repository_root,
        target_file=approved_change.target_file,
    )

    if not target_path.is_file():
        raise ValueError(
            f"GitOps target file does not exist: "
            f"{approved_change.target_file}"
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

    rendered_documents = deepcopy(
        documents,
    )

    document = _find_manifest_document(
        documents=rendered_documents,
        kind=approved_change.manifest_kind,
        name=approved_change.manifest_name,
    )

    pod_spec = _get_pod_spec(
        document,
    )

    container = _find_container(
        pod_spec=pod_spec,
        container_name=approved_change.container_name,
    )

    resources = container.setdefault(
        "resources",
        {},
    )

    if not isinstance(
        resources,
        dict,
    ):
        raise ValueError(
            "Container resources field must be a mapping."
        )

    requests = resources.setdefault(
        "requests",
        {},
    )

    if not isinstance(
        requests,
        dict,
    ):
        raise ValueError(
            "Container resource requests must be a mapping."
        )

    if (
        approved_change.approved_cpu_request
        is not None
    ):
        requests["cpu"] = (
            approved_change.approved_cpu_request
        )

    if (
        approved_change.approved_memory_request
        is not None
    ):
        requests["memory"] = (
            approved_change.approved_memory_request
        )

    rendered_yaml = yaml.safe_dump_all(
        rendered_documents,
        sort_keys=False,
    )

    return ApprovedFinOpsManifest(
        target_file=approved_change.target_file,
        manifest_kind=approved_change.manifest_kind,
        manifest_name=approved_change.manifest_name,
        container_name=approved_change.container_name,
        approved_cpu_request=(
            approved_change.approved_cpu_request
        ),
        approved_memory_request=(
            approved_change.approved_memory_request
        ),
        rendered_yaml=rendered_yaml,
        ready_for_commit=True,
        writes_file=False,
        writes_git=False,
    )
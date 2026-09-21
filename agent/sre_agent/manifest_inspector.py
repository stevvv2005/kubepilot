from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ContainerManifestState:
    name: str
    image: Optional[str]
    memory_limit: Optional[str]
    readiness_path: Optional[str]
    readiness_port: Optional[Any]


def inspect_container(
    manifest: Dict[str, Any],
    container_name: str,
) -> ContainerManifestState:
    """
    Inspect a container definition from a Kubernetes manifest.

    Read-only:
    - no file writes
    - no Kubernetes writes
    """

    spec = manifest.get("spec", {})

    if manifest.get("kind") in {"Deployment", "StatefulSet", "DaemonSet"}:
        spec = spec.get("template", {}).get("spec", {})

    containers = spec.get("containers", [])

    for container in containers:
        if container.get("name") != container_name:
            continue

        memory_limit = (
            container.get("resources", {})
            .get("limits", {})
            .get("memory")
        )

        readiness_probe = container.get("readinessProbe", {})
        http_get = readiness_probe.get("httpGet", {})

        return ContainerManifestState(
            name=container_name,
            image=container.get("image"),
            memory_limit=memory_limit,
            readiness_path=http_get.get("path"),
            readiness_port=http_get.get("port"),
        )

    raise ValueError(
        f"Container not found in manifest: {container_name}"
    )

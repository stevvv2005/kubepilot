from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class TargetFileResolution:
    namespace: str
    pod_name: str
    container_name: str
    target_file: Optional[str]
    matched: bool
    reason: str


_ALLOWED_TARGETS: Dict[Tuple[str, str, str], str] = {
    (
        "default",
        "kubepilot-oomkilled",
        "memory-hog",
    ): "chaos/oomkilled-pod.yaml",
    (
        "default",
        "kubepilot-imagepullbackoff",
        "broken-container",
    ): "chaos/imagepullbackoff-pod.yaml",
    (
        "default",
        "kubepilot-readiness-failed",
        "web",
    ): "chaos/readiness-failed-pod.yaml",
}


def _is_safe_repo_path(path: str) -> bool:
    """
    Accept only relative repository paths.

    Reject:
    - absolute paths
    - path traversal
    - empty paths
    """

    if not path:
        return False

    normalized = PurePosixPath(path)

    if normalized.is_absolute():
        return False

    if ".." in normalized.parts:
        return False

    return True


def is_allowlisted_target_file(path: str) -> bool:
    """
    Return whether a repository path came from the trusted SRE allowlist.
    """

    if not _is_safe_repo_path(path):
        return False

    return path in _ALLOWED_TARGETS.values()


def resolve_target_file(
    namespace: str,
    pod_name: str,
    container_name: str,
) -> TargetFileResolution:
    """
    Resolve a Kubernetes incident to an allowlisted GitOps file.

    This resolver never accepts a target path from the alert itself.
    It only returns paths explicitly defined in the allowlist.
    """

    key = (
        namespace,
        pod_name,
        container_name,
    )

    target_file = _ALLOWED_TARGETS.get(key)

    if target_file is None:
        return TargetFileResolution(
            namespace=namespace,
            pod_name=pod_name,
            container_name=container_name,
            target_file=None,
            matched=False,
            reason=(
                "No allowlisted GitOps target file matches "
                "this namespace, pod, and container."
            ),
        )

    if not _is_safe_repo_path(target_file):
        return TargetFileResolution(
            namespace=namespace,
            pod_name=pod_name,
            container_name=container_name,
            target_file=None,
            matched=False,
            reason="Resolved target file failed repository path safety checks.",
        )

    return TargetFileResolution(
        namespace=namespace,
        pod_name=pod_name,
        container_name=container_name,
        target_file=target_file,
        matched=True,
        reason="Resolved target file from the trusted allowlist.",
    )

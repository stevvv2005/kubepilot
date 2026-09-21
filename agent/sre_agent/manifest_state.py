from agent.sre_agent.manifest_inspector import ContainerManifestState, inspect_container
from agent.sre_agent.manifest_reader import read_manifest


def get_container_manifest_state(
    manifest_path: str,
    container_name: str,
) -> ContainerManifestState:
    """
    Read a Kubernetes manifest and inspect one container.

    Read-only:
    - does not modify the manifest
    - does not commit anything
    - does not modify Kubernetes
    """

    manifest = read_manifest(manifest_path)

    return inspect_container(
        manifest=manifest,
        container_name=container_name,
    )

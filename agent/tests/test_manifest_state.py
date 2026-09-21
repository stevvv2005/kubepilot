from agent.sre_agent.manifest_state import get_container_manifest_state


def test_get_real_imagepullbackoff_manifest_state():
    state = get_container_manifest_state(
        manifest_path="chaos/imagepullbackoff-pod.yaml",
        container_name="broken-container",
    )

    assert state.name == "broken-container"
    assert state.image == (
        "ghcr.io/kubepilot/this-image-does-not-exist:never"
    )

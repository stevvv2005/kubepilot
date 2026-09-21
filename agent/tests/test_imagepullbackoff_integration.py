import subprocess

import pytest

from agent.mcp_servers.kubernetes import get_pod_incident_context
from agent.sre_agent.diagnostic import diagnose


pytestmark = pytest.mark.integration


def pod_exists(name: str) -> bool:
    result = subprocess.run(
        ["kubectl", "get", "pod", name, "-n", "default"],
        capture_output=True,
        text=True,
        check=False,
    )

    return result.returncode == 0


def test_real_imagepullbackoff_incident():
    if not pod_exists("kubepilot-imagepullbackoff"):
        pytest.skip("ImagePullBackOff scenario pod is not running")

    context = get_pod_incident_context(
        namespace="default",
        pod_name="kubepilot-imagepullbackoff",
        container_name="broken-container",
    )

    result = diagnose(context)

    assert context.waiting_reason == "ImagePullBackOff"
    assert result.incident_type == "ImagePullBackOff"
    assert result.confidence == "high"

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


def test_real_oomkilled_incident():
    if not pod_exists("kubepilot-oomkilled"):
        pytest.skip("OOMKilled scenario pod is not running")

    context = get_pod_incident_context(
        namespace="default",
        pod_name="kubepilot-oomkilled",
        container_name="memory-hog",
    )

    result = diagnose(context)

    assert context.terminated_reason == "OOMKilled"
    assert context.restart_count > 0
    assert result.incident_type == "OOMKilled"
    assert result.confidence == "high"

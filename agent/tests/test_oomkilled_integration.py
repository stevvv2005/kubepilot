import pytest

from agent.mcp_servers.kubernetes import get_pod_incident_context
from agent.sre_agent.diagnostic import diagnose


pytestmark = pytest.mark.integration


def test_real_oomkilled_incident():
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

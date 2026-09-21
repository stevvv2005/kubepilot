import pytest

from agent.mcp_servers.kubernetes import get_pod_incident_context
from agent.sre_agent.diagnostic import diagnose


pytestmark = pytest.mark.integration


def test_real_readiness_probe_failed_incident():
    context = get_pod_incident_context(
        namespace="default",
        pod_name="kubepilot-readiness-failed",
        container_name="web",
    )

    result = diagnose(context)

    assert context.readiness_failed is True
    assert result.incident_type == "ReadinessProbeFailed"
    assert result.confidence == "medium"

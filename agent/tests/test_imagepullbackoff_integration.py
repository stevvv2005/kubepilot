from agent.mcp_servers.kubernetes import get_pod_incident_context
from agent.sre_agent.diagnostic import diagnose


def test_real_imagepullbackoff_incident():
    context = get_pod_incident_context(
        namespace="default",
        pod_name="kubepilot-imagepullbackoff",
        container_name="broken-container",
    )

    result = diagnose(context)

    assert context.waiting_reason == "ImagePullBackOff"
    assert result.incident_type == "ImagePullBackOff"
    assert result.confidence == "high"
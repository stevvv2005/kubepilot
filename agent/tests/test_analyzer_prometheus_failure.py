from urllib.error import URLError
from unittest.mock import patch

from agent.sre_agent.analyzer import analyze_pod
from agent.sre_agent.diagnostic import IncidentContext


@patch("agent.sre_agent.analyzer.get_pod_metrics")
@patch("agent.sre_agent.analyzer.get_pod_incident_context")
def test_analysis_continues_when_prometheus_is_unavailable(
    mock_get_pod_incident_context,
    mock_get_pod_metrics,
):
    mock_get_pod_incident_context.return_value = IncidentContext(
        namespace="default",
        pod_name="kubepilot-oomkilled",
        container_name="memory-hog",
        terminated_reason="OOMKilled",
        restart_count=1,
    )

    mock_get_pod_metrics.side_effect = URLError(
        "Prometheus connection refused"
    )

    analysis = analyze_pod(
        namespace="default",
        pod_name="kubepilot-oomkilled",
        container_name="memory-hog",
    )

    assert analysis.diagnosis.incident_type == "OOMKilled"
    assert analysis.diagnosis.confidence == "high"

    assert analysis.memory_mib is None
    assert analysis.cpu_millicores is None

    mock_get_pod_incident_context.assert_called_once_with(
        namespace="default",
        pod_name="kubepilot-oomkilled",
        container_name="memory-hog",
    )

    mock_get_pod_metrics.assert_called_once()

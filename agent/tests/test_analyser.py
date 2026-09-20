
from agent.sre_agent.analyzer import analyze_pod


def test_analyze_real_frontend():
    result = analyze_pod(
        namespace="default",
        pod_name="frontend-58b4dc4d4d-hg2f8",
        container_name="server",
    )

    assert result.diagnosis.incident_type == "Healthy"
    assert result.memory_mib > 0
    assert result.cpu_millicores >= 0

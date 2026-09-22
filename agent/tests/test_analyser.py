import pytest

from agent.sre_agent.analyzer import analyze_pod


@pytest.mark.integration
def test_analyze_real_frontend():
    analysis = analyze_pod(
        namespace="default",
        pod_name="frontend",
        container_name="server",
    )

    assert analysis.namespace == "default"
    assert analysis.pod_name == "frontend"
    assert analysis.container_name == "server"
    assert analysis.diagnosis is not None
from agent.sre_agent.diagnostic import IncidentContext, diagnose


def test_diagnose_oomkilled():
    context = IncidentContext(
        namespace="default",
        pod_name="checkoutservice-123",
        container_name="server",
        terminated_reason="OOMKilled",
        restart_count=3,
    )

    result = diagnose(context)

    assert result.incident_type == "OOMKilled"
    assert result.confidence == "high"
    assert "memory limit" in result.root_cause
    assert "Git" in result.recommendation


def test_diagnose_image_pull_backoff():
    context = IncidentContext(
        namespace="default",
        pod_name="frontend-123",
        container_name="server",
        waiting_reason="ImagePullBackOff",
    )

    result = diagnose(context)

    assert result.incident_type == "ImagePullBackOff"
    assert result.confidence == "high"
    assert "pull the image" in result.root_cause
    assert "imagePullSecrets" in result.recommendation


def test_diagnose_readiness_probe_failed():
    context = IncidentContext(
        namespace="default",
        pod_name="paymentservice-123",
        container_name="server",
        readiness_failed=True,
    )

    result = diagnose(context)

    assert result.incident_type == "ReadinessProbeFailed"
    assert result.confidence == "medium"
    assert "readiness probe" in result.root_cause
    assert "Git/PR" in result.recommendation


def test_diagnose_healthy():
    context = IncidentContext(
        namespace="default",
        pod_name="frontend-123",
        container_name="server",
        waiting_reason=None,
        terminated_reason=None,
        restart_count=2,
        readiness_failed=False,
    )

    result = diagnose(context)

    assert result.incident_type == "Healthy"
    assert result.confidence == "high"
    assert "No active Kubernetes incident" in result.root_cause
def test_diagnose_oomkilled_with_metrics():
    from agent.sre_agent.diagnostic import RuntimeMetrics

    context = IncidentContext(
        namespace="default",
        pod_name="checkoutservice-123",
        container_name="server",
        terminated_reason="OOMKilled",
        restart_count=4,
    )

    metrics = RuntimeMetrics(
        memory_mib=245.75,
        cpu_millicores=82.4,
    )

    result = diagnose(context, metrics)

    assert result.incident_type == "OOMKilled"
    assert result.confidence == "high"
    assert "245.75 MiB" in result.root_cause
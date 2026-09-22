from unittest.mock import patch

from fastapi.testclient import TestClient

from agent.sre_agent.analyzer import PodAnalysis
from agent.sre_agent.diagnostic import Diagnosis
from agent.webhook.app import app


client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_alert_without_required_labels_is_rejected():
    payload = {
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "KubePilotPodIncident",
                    "namespace": "default",
                },
                "annotations": {},
            }
        ],
    }

    response = client.post("/alerts", json=payload)

    assert response.status_code == 400
    assert "namespace, pod, and container" in response.json()["detail"]


@patch("agent.webhook.app.analyze_pod")
def test_alert_triggers_sre_analysis(mock_analyze_pod):
    mock_analyze_pod.return_value = PodAnalysis(
        namespace="default",
        pod_name="frontend-test",
        container_name="server",
        diagnosis=Diagnosis(
            incident_type="Healthy",
            root_cause="No active Kubernetes incident was detected.",
            recommendation="No corrective action is required.",
            confidence="high",
        ),
        memory_mib=18.5,
        cpu_millicores=30.2,
    )

    payload = {
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "KubePilotPodIncident",
                    "namespace": "default",
                    "pod": "frontend-test",
                    "container": "server",
                    "severity": "warning",
                },
                "annotations": {
                    "summary": "Webhook test",
                },
            }
        ],
    }

    response = client.post("/alerts", json=payload)

    assert response.status_code == 200

    body = response.json()

    assert body["received"] == 1
    assert body["status"] == "firing"
    assert body["alertname"] == "KubePilotPodIncident"
    assert body["namespace"] == "default"
    assert body["pod"] == "frontend-test"
    assert body["container"] == "server"
    assert body["severity"] == "warning"

    assert body["diagnosis"]["incident_type"] == "Healthy"
    assert body["diagnosis"]["root_cause"] == (
        "No active Kubernetes incident was detected."
    )
    assert body["diagnosis"]["recommendation"] == (
        "No corrective action is required."
    )
    assert body["diagnosis"]["confidence"] == "high"

    assert body["metrics"]["memory_mib"] == 18.5
    assert body["metrics"]["cpu_millicores"] == 30.2

    assert body["remediation"]["incident_type"] == "Healthy"
    assert body["remediation"]["summary"] == "No remediation required."
    assert body["remediation"]["proposed_change"] == (
        "No Git change is required."
    )
    assert body["remediation"]["target_file"] is None
    assert body["remediation"]["requires_human_approval"] is True
    assert body["remediation"]["direct_cluster_write"] is False

    assert body["git_change"]["incident_type"] == "Healthy"
    assert body["git_change"]["target_file"] is None
    assert body["git_change"]["change_type"] == "none"
    assert body["git_change"]["description"] == (
        "No Git change is required."
    )
    assert body["git_change"]["requires_human_approval"] is True
    assert body["git_change"]["apply_directly"] is False

    assert body["manifest_diff"]["incident_type"] == "Healthy"
    assert body["manifest_diff"]["target_file"] is None
    assert body["manifest_diff"]["change_type"] == "none"
    assert body["manifest_diff"]["before"] is None
    assert body["manifest_diff"]["after"] is None
    assert body["manifest_diff"]["requires_human_approval"] is True
    assert body["manifest_diff"]["writes_file"] is False

    assert body["patch_proposal"]["incident_type"] == "Healthy"
    assert body["patch_proposal"]["target_file"] is None
    assert body["patch_proposal"]["container_name"] is None
    assert body["patch_proposal"]["field"] == "none"
    assert body["patch_proposal"]["current_value"] is None
    assert body["patch_proposal"]["proposed_value"] is None
    assert body["patch_proposal"]["reason"] == "No patch is required."
    assert body["patch_proposal"]["requires_human_approval"] is True
    assert body["patch_proposal"]["writes_file"] is False

    mock_analyze_pod.assert_called_once_with(
        namespace="default",
        pod_name="frontend-test",
        container_name="server",
    )

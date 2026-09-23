from types import SimpleNamespace
from unittest.mock import patch

import yaml
from fastapi.testclient import TestClient

from agent.webhook.app import app


client = TestClient(app)


@patch("agent.webhook.app.analyze_pod")
def test_approve_oom_remediation(mock_analyze_pod):
    mock_analyze_pod.return_value = SimpleNamespace(
        namespace="default",
        pod_name="kubepilot-oomkilled",
        container_name="memory-hog",
        diagnosis=SimpleNamespace(
            incident_type="OOMKilled",
            root_cause="Container exceeded its memory limit.",
            recommendation="Review memory and propose Git change.",
            confidence="high",
        ),
        memory_mib=None,
        cpu_millicores=None,
    )

    response = client.post(
        "/approvals",
        json={
            "namespace": "default",
            "pod_name": "kubepilot-oomkilled",
            "container_name": "memory-hog",
            "approved": True,
            "approved_value": "64Mi",
            "reviewer": "human-reviewer",
            "reason": "Reviewed and approved.",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["approval"]["approved"] is True
    assert body["approval"]["approved_value"] == "64Mi"
    assert body["approval"]["reviewer"] == "human-reviewer"

    assert body["target_file_resolution"]["matched"] is True
    assert body["target_file_resolution"]["target_file"] == (
        "chaos/oomkilled-pod.yaml"
    )

    assert body["candidate_value"]["candidate_value"] == "64Mi"
    assert body["candidate_value"]["auto_apply"] is False

    assert body["reviewed_patch"]["approved_value"] == "64Mi"
    assert body["reviewed_patch"]["ready_for_pr"] is True
    assert body["reviewed_patch"]["writes_file"] is False
    assert body["reviewed_patch"]["auto_apply"] is False

    # Approved manifest rendered entirely in memory.
    assert body["approved_manifest"] is not None
    assert body["approved_manifest"]["target_file"] == (
        "chaos/oomkilled-pod.yaml"
    )
    assert body["approved_manifest"]["container_name"] == "memory-hog"
    assert body["approved_manifest"]["field"] == (
        "resources.limits.memory"
    )
    assert body["approved_manifest"]["approved_value"] == "64Mi"
    assert body["approved_manifest"]["ready_for_commit"] is True
    assert body["approved_manifest"]["writes_file"] is False
    assert body["approved_manifest"]["writes_git"] is False

    rendered = yaml.safe_load(
        body["approved_manifest"]["rendered_yaml"]
    )

    container = rendered["spec"]["containers"][0]

    assert container["name"] == "memory-hog"
    assert container["resources"]["limits"]["memory"] == "64Mi"

    # PR preparation becomes eligible after explicit human approval.
    assert body["pr_payload"]["approved_value"] == "64Mi"
    assert body["pr_payload"]["ready_to_create"] is True
    assert body["pr_payload"]["writes_git"] is False
    assert body["pr_payload"]["creates_pr"] is False

    assert body["github_pr_gateway"]["allowed"] is True
    assert body["github_pr_gateway"]["ready_to_send"] is True
    assert body["github_pr_gateway"]["performs_write"] is False

    assert body["github_pr_request"]["approved_value"] == "64Mi"
    assert body["github_pr_request"]["ready_to_send"] is True
    assert body["github_pr_request"]["performs_write"] is False


@patch("agent.webhook.app.analyze_pod")
def test_rejected_approval_does_not_render_manifest(
    mock_analyze_pod,
):
    mock_analyze_pod.return_value = SimpleNamespace(
        namespace="default",
        pod_name="kubepilot-oomkilled",
        container_name="memory-hog",
        diagnosis=SimpleNamespace(
            incident_type="OOMKilled",
            root_cause="Container exceeded its memory limit.",
            recommendation="Review memory and propose Git change.",
            confidence="high",
        ),
        memory_mib=None,
        cpu_millicores=None,
    )

    response = client.post(
        "/approvals",
        json={
            "namespace": "default",
            "pod_name": "kubepilot-oomkilled",
            "container_name": "memory-hog",
            "approved": False,
            "approved_value": None,
            "reviewer": "human-reviewer",
            "reason": "More investigation required.",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["approval"]["approved"] is False

    assert body["reviewed_patch"]["approved_value"] is None
    assert body["reviewed_patch"]["ready_for_pr"] is False

    # No approved YAML may be produced after rejection.
    assert body["approved_manifest"] is None

    assert body["pr_payload"]["ready_to_create"] is False

    assert body["github_pr_gateway"]["allowed"] is False
    assert body["github_pr_gateway"]["ready_to_send"] is False
    assert body["github_pr_gateway"]["performs_write"] is False

    assert body["github_pr_request"]["ready_to_send"] is False
    assert body["github_pr_request"]["performs_write"] is False


def test_approval_rejects_unknown_workload():
    response = client.post(
        "/approvals",
        json={
            "namespace": "default",
            "pod_name": "unknown-pod",
            "container_name": "unknown-container",
            "approved": True,
            "approved_value": "64Mi",
            "reviewer": "human-reviewer",
            "reason": "Approved.",
        },
    )

    assert response.status_code == 400

    assert "No allowlisted GitOps target file" in (
        response.json()["detail"]
    )

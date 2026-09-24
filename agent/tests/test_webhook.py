from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import agent.webhook.app as webhook_app
from agent.observability.metrics import kubepilot_metrics
from agent.webhook.app import app


client = TestClient(app)


METRIC_NAMES = (
    "kubepilot_incidents_total",
    "kubepilot_approvals_total",
    "kubepilot_rejections_total",
    "kubepilot_prs_created_total",
    "kubepilot_github_execution_failures_total",
    "kubepilot_slack_callbacks_total",
    "kubepilot_llm_requests_total",
)


def _metric_value(metric_name):
    return kubepilot_metrics.snapshot()[metric_name]


def _oom_analysis():
    return SimpleNamespace(
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


def _approval_payload(*, approved=True):
    return {
        "namespace": "default",
        "pod_name": "kubepilot-oomkilled",
        "container_name": "memory-hog",
        "approved": approved,
        "approved_value": "64Mi" if approved else None,
        "reviewer": "metrics-test-reviewer",
        "reason": "Metrics test decision.",
    }


def _github_execution_result(*, executed):
    return SimpleNamespace(
        repository="stevvv2005/kubepilot",
        base_branch="main",
        head_branch="fix/sre-oomkilled",
        target_file="chaos/oomkilled-pod.yaml",
        commit_sha="test-sha" if executed else None,
        pr_number=101 if executed else None,
        pr_url=(
            "https://github.test/pull/101"
            if executed
            else None
        ),
        executed=executed,
        performs_cluster_write=False,
    )


def _configure_mock_live_github(monkeypatch, executor):
    monkeypatch.setenv(
        "KUBEPILOT_GITHUB_LIVE_AUTHORIZED",
        "true",
    )
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setattr(
        webhook_app,
        "GitHubRESTConfig",
        lambda **kwargs: SimpleNamespace(**kwargs),
    )
    monkeypatch.setattr(
        webhook_app,
        "GitHubRESTClient",
        lambda **kwargs: SimpleNamespace(**kwargs),
    )
    monkeypatch.setattr(
        webhook_app,
        "execute_sre_github_pr_request",
        executor,
    )


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@patch("agent.webhook.app.analyze_pod")
def test_receive_alert(mock_analyze_pod):
    incidents_before = _metric_value("kubepilot_incidents_total")
    mock_analyze_pod.return_value = SimpleNamespace(
        namespace="default",
        pod_name="frontend",
        container_name="server",
        diagnosis=SimpleNamespace(
            incident_type="Healthy",
            root_cause="No known incident detected.",
            recommendation=(
                "No remediation required. "
                "Continue monitoring the workload."
            ),
            confidence="high",
        ),
        memory_mib=128.0,
        cpu_millicores=25.0,
    )

    payload = {
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "KubePilotPodIncident",
                    "namespace": "default",
                    "pod": "frontend",
                    "container": "server",
                    "severity": "warning",
                },
                "annotations": {
                    "summary": "Test alert",
                },
            }
        ],
    }

    response = client.post(
        "/alerts",
        json=payload,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["received"] == 1
    assert body["status"] == "firing"
    assert body["alertname"] == "KubePilotPodIncident"
    assert body["namespace"] == "default"
    assert body["pod"] == "frontend"
    assert body["container"] == "server"
    assert body["severity"] == "warning"

    # Target file resolver
    assert body["target_file_resolution"]["namespace"] == "default"
    assert body["target_file_resolution"]["pod_name"] == "frontend"
    assert body["target_file_resolution"]["container_name"] == "server"
    assert body["target_file_resolution"]["target_file"] is None
    assert body["target_file_resolution"]["matched"] is False
    assert "No allowlisted GitOps target file" in (
        body["target_file_resolution"]["reason"]
    )

    # Diagnosis
    assert body["diagnosis"]["incident_type"] == "Healthy"
    assert body["diagnosis"]["root_cause"] == (
        "No known incident detected."
    )
    assert body["diagnosis"]["confidence"] == "high"

    # Metrics
    assert body["metrics"]["memory_mib"] == 128.0
    assert body["metrics"]["cpu_millicores"] == 25.0
        # LLM analysis
    assert body["llm_status"]["available"] is True

    assert (
        body["llm_status"]["error"]
        is None
    )

    assert (
        body["llm_status"]["non_blocking"]
        is True
    )

    assert (
        body["llm_analysis"]["provider"]
        == "mock"
    )

    assert (
        body["llm_analysis"]["model"]
        == "kubepilot-mock-v1"
    )

    assert (
        body["llm_analysis"]
        ["requires_human_approval"]
        is True
    )

    assert (
        body["llm_analysis"]
        ["allows_direct_cluster_write"]
        is False
    )

    assert (
        body["llm_analysis"]
        ["external_request_performed"]
        is False
    )

    assert (
        body["llm_analysis"]
        ["performs_write"]
        is False
    )
    # Remediation
    assert body["remediation"]["incident_type"] == "Healthy"
    assert body["remediation"]["target_file"] is None
    assert body["remediation"]["requires_human_approval"] is True
    assert body["remediation"]["direct_cluster_write"] is False

    # Git change
    assert body["git_change"]["incident_type"] == "Healthy"
    assert body["git_change"]["target_file"] is None
    assert body["git_change"]["change_type"] == "none"
    assert body["git_change"]["requires_human_approval"] is True
    assert body["git_change"]["apply_directly"] is False

    # Manifest diff
    assert body["manifest_diff"]["incident_type"] == "Healthy"
    assert body["manifest_diff"]["target_file"] is None
    assert body["manifest_diff"]["change_type"] == "none"
    assert body["manifest_diff"]["requires_human_approval"] is True
    assert body["manifest_diff"]["writes_file"] is False

    # Patch proposal
    assert body["patch_proposal"]["incident_type"] == "Healthy"
    assert body["patch_proposal"]["target_file"] is None
    assert body["patch_proposal"]["container_name"] is None
    assert body["patch_proposal"]["field"] == "none"
    assert body["patch_proposal"]["requires_human_approval"] is True
    assert body["patch_proposal"]["writes_file"] is False

    # Candidate value
    assert body["candidate_value"]["incident_type"] == "Healthy"
    assert body["candidate_value"]["field"] == "none"
    assert body["candidate_value"]["candidate_value"] is None
    assert body["candidate_value"]["confidence"] == "high"
    assert body["candidate_value"]["requires_human_approval"] is True
    assert body["candidate_value"]["auto_apply"] is False

    # Reviewed patch
    assert body["reviewed_patch"]["incident_type"] == "Healthy"
    assert body["reviewed_patch"]["target_file"] is None
    assert body["reviewed_patch"]["container_name"] is None
    assert body["reviewed_patch"]["approved_value"] is None
    assert body["reviewed_patch"]["ready_for_pr"] is False
    assert body["reviewed_patch"]["writes_file"] is False
    assert body["reviewed_patch"]["auto_apply"] is False

    # PR payload
    assert body["pr_payload"]["incident_type"] == "Healthy"
    assert body["pr_payload"]["title"] == (
        "fix(sre): review Healthy remediation"
    )
    assert body["pr_payload"]["branch_name"] == (
        "fix/sre-healthy-pending"
    )
    assert body["pr_payload"]["target_file"] is None
    assert body["pr_payload"]["container_name"] is None
    assert body["pr_payload"]["approved_value"] is None
    assert body["pr_payload"]["ready_to_create"] is False
    assert body["pr_payload"]["writes_git"] is False
    assert body["pr_payload"]["creates_pr"] is False

    # GitHub PR safety gateway
    assert body["github_pr_gateway"]["allowed"] is False
    assert body["github_pr_gateway"]["ready_to_send"] is False
    assert body["github_pr_gateway"]["performs_write"] is False
    assert "not approved" in body["github_pr_gateway"]["reason"]

    # GitHub PR request
    assert body["github_pr_request"]["repository"] == (
        "stevvv2005/kubepilot"
    )
    assert body["github_pr_request"]["base_branch"] == "main"
    assert body["github_pr_request"]["head_branch"] == (
        "fix/sre-healthy-pending"
    )
    assert body["github_pr_request"]["title"] == (
        "fix(sre): review Healthy remediation"
    )
    assert body["github_pr_request"]["target_file"] is None
    assert body["github_pr_request"]["approved_value"] is None
    assert body["github_pr_request"]["ready_to_send"] is False
    assert body["github_pr_request"]["performs_write"] is False

    mock_analyze_pod.assert_called_once_with(
        namespace="default",
        pod_name="frontend",
        container_name="server",
    )
    assert _metric_value("kubepilot_incidents_total") == (
        incidents_before + 1
    )


def test_receive_alert_without_alerts():
    response = client.post(
        "/alerts",
        json={
            "status": "firing",
            "alerts": [],
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Alertmanager payload contains no alerts"
    )
@patch(
    "agent.webhook.app.run_llm_workflow"
)
@patch(
    "agent.webhook.app.analyze_pod"
)
def test_llm_failure_does_not_block_alert_pipeline(
    mock_analyze_pod,
    mock_llm_workflow,
):
    mock_analyze_pod.return_value = (
        SimpleNamespace(
            namespace="default",
            pod_name="frontend",
            container_name="server",
            diagnosis=SimpleNamespace(
                incident_type="Healthy",
                root_cause=(
                    "No known incident detected."
                ),
                recommendation=(
                    "Continue monitoring."
                ),
                confidence="high",
            ),
            memory_mib=128.0,
            cpu_millicores=25.0,
        )
    )

    mock_llm_workflow.side_effect = (
        RuntimeError(
            "Simulated LLM failure"
        )
    )

    payload = {
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": (
                        "KubePilotPodIncident"
                    ),
                    "namespace": "default",
                    "pod": "frontend",
                    "container": "server",
                    "severity": "warning",
                },
                "annotations": {
                    "summary": "Test alert",
                },
            }
        ],
    }

    response = client.post(
        "/alerts",
        json=payload,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["diagnosis"][
        "incident_type"
    ] == "Healthy"

    assert body["llm_analysis"] is None

    assert (
        body["llm_status"]["available"]
        is False
    )

    assert (
        "Simulated LLM failure"
        in body["llm_status"]["error"]
    )

    assert (
        body["llm_status"]["non_blocking"]
        is True
    )


def test_metrics_endpoint():
    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")

    body = response.text

    for metric_name in METRIC_NAMES:
        assert f"# TYPE {metric_name} counter" in body
        assert f"{metric_name} " in body


@pytest.mark.parametrize(
    ("approved", "incremented_metric", "unchanged_metric"),
    [
        (
            True,
            "kubepilot_approvals_total",
            "kubepilot_rejections_total",
        ),
        (
            False,
            "kubepilot_rejections_total",
            "kubepilot_approvals_total",
        ),
    ],
)
def test_approval_decision_counter_increment(
    monkeypatch,
    approved,
    incremented_metric,
    unchanged_metric,
):
    monkeypatch.setenv(
        "KUBEPILOT_GITHUB_LIVE_AUTHORIZED",
        "false",
    )
    monkeypatch.setattr(
        webhook_app,
        "analyze_pod",
        lambda **kwargs: _oom_analysis(),
    )
    before = kubepilot_metrics.snapshot()

    response = client.post(
        "/approvals",
        json=_approval_payload(approved=approved),
    )

    assert response.status_code == 200
    after = kubepilot_metrics.snapshot()
    assert after[incremented_metric] == before[incremented_metric] + 1
    assert after[unchanged_metric] == before[unchanged_metric]


def test_slack_callback_counter_increment(monkeypatch):
    monkeypatch.delenv("SLACK_SIGNING_SECRET", raising=False)
    before = _metric_value("kubepilot_slack_callbacks_total")

    response = client.post("/slack/actions", content=b"")

    assert response.status_code == 503
    assert _metric_value("kubepilot_slack_callbacks_total") == before + 1


def test_llm_request_counter_increment(monkeypatch):
    monkeypatch.setenv("KUBEPILOT_LLM_PROVIDER", "mock")
    before = _metric_value("kubepilot_llm_requests_total")

    response = client.post(
        "/llm/analyze",
        json={
            "query": "Explain an OOMKilled incident.",
            "signal_type": "sre_incident",
            "namespace": "default",
            "workload_name": "checkoutservice",
        },
    )

    assert response.status_code == 200
    assert _metric_value("kubepilot_llm_requests_total") == before + 1


def test_pr_counter_increments_only_for_executed_live_result(
    monkeypatch,
):
    monkeypatch.setattr(
        webhook_app,
        "analyze_pod",
        lambda **kwargs: _oom_analysis(),
    )
    results = iter(
        (
            _github_execution_result(executed=False),
            _github_execution_result(executed=True),
        )
    )
    _configure_mock_live_github(
        monkeypatch,
        lambda **kwargs: next(results),
    )
    before = _metric_value("kubepilot_prs_created_total")

    not_executed = client.post(
        "/approvals",
        json=_approval_payload(),
    )

    assert not_executed.status_code == 200
    assert _metric_value("kubepilot_prs_created_total") == before

    executed = client.post(
        "/approvals",
        json=_approval_payload(),
    )

    assert executed.status_code == 200
    assert executed.json()["github_live_execution"]["result"][
        "executed"
    ] is True
    assert _metric_value("kubepilot_prs_created_total") == before + 1


def test_github_failure_counter_increments_on_live_failure(
    monkeypatch,
):
    monkeypatch.setattr(
        webhook_app,
        "analyze_pod",
        lambda **kwargs: _oom_analysis(),
    )

    def fail_live_execution(**kwargs):
        raise ValueError("Simulated GitHub execution failure.")

    _configure_mock_live_github(monkeypatch, fail_live_execution)
    failures_before = _metric_value(
        "kubepilot_github_execution_failures_total"
    )
    prs_before = _metric_value("kubepilot_prs_created_total")

    response = client.post(
        "/approvals",
        json=_approval_payload(),
    )

    assert response.status_code == 400
    assert _metric_value(
        "kubepilot_github_execution_failures_total"
    ) == failures_before + 1
    assert _metric_value("kubepilot_prs_created_total") == prs_before

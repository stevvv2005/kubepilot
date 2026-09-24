from types import SimpleNamespace
from unittest.mock import patch

import yaml
from fastapi.testclient import TestClient

import agent.webhook.app as webhook_app
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

    # Human approval
    assert body["approval"]["approved"] is True
    assert body["approval"]["approved_value"] == "64Mi"
    assert body["approval"]["reviewer"] == "human-reviewer"

    # Target resolver
    assert body["target_file_resolution"]["matched"] is True
    assert body["target_file_resolution"]["target_file"] == (
        "chaos/oomkilled-pod.yaml"
    )

    # Candidate
    assert body["candidate_value"]["candidate_value"] == "64Mi"
    assert body["candidate_value"]["auto_apply"] is False

    # Reviewed patch
    assert body["reviewed_patch"]["approved_value"] == "64Mi"
    assert body["reviewed_patch"]["ready_for_pr"] is True
    assert body["reviewed_patch"]["writes_file"] is False
    assert body["reviewed_patch"]["auto_apply"] is False

    # Approved manifest
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

    rendered_manifest = yaml.safe_load(
        body["approved_manifest"]["rendered_yaml"]
    )

    container = rendered_manifest["spec"]["containers"][0]

    assert container["name"] == "memory-hog"
    assert container["resources"]["limits"]["memory"] == "64Mi"

    # PR payload
    assert body["pr_payload"]["approved_value"] == "64Mi"
    assert body["pr_payload"]["branch_name"] == "fix/sre-oomkilled"
    assert body["pr_payload"]["commit_message"] == (
        "fix(sre): remediate OOMKilled"
    )
    assert body["pr_payload"]["ready_to_create"] is True
    assert body["pr_payload"]["writes_git"] is False
    assert body["pr_payload"]["creates_pr"] is False

    # Git commit dry-run
    assert body["git_commit_dry_run"] is not None

    assert body["git_commit_dry_run"]["target_file"] == (
        "chaos/oomkilled-pod.yaml"
    )
    assert body["git_commit_dry_run"]["branch_name"] == (
        "fix/sre-oomkilled"
    )
    assert body["git_commit_dry_run"]["commit_message"] == (
        "fix(sre): remediate OOMKilled"
    )
    assert "memory: 64Mi" in (
        body["git_commit_dry_run"]["rendered_yaml"]
    )
    assert body["git_commit_dry_run"]["ready_to_commit"] is True
    assert body["git_commit_dry_run"]["performs_write"] is False
    assert body["git_commit_dry_run"]["writes_file"] is False
    assert body["git_commit_dry_run"]["writes_git"] is False

    # Git execution gateway
    assert body["git_execution_gateway"] is not None
    assert body["git_execution_gateway"]["allowed"] is True
    assert (
        body["git_execution_gateway"]["ready_to_execute"]
        is True
    )
    assert body["git_execution_gateway"]["performs_write"] is False

    # GitHub gateway
    assert body["github_pr_gateway"]["allowed"] is True
    assert body["github_pr_gateway"]["ready_to_send"] is True
    assert body["github_pr_gateway"]["performs_write"] is False

    # GitHub request
    assert body["github_pr_request"]["repository"] == (
        "stevvv2005/kubepilot"
    )
    assert body["github_pr_request"]["base_branch"] == "main"
    assert body["github_pr_request"]["head_branch"] == (
        "fix/sre-oomkilled"
    )
    assert body["github_pr_request"]["approved_value"] == "64Mi"
    assert body["github_pr_request"]["ready_to_send"] is True
    assert body["github_pr_request"]["performs_write"] is False

    # Git execution request
    assert body["git_execution_request"] is not None

    assert body["git_execution_request"]["repository"] == (
        "stevvv2005/kubepilot"
    )
    assert body["git_execution_request"]["base_branch"] == "main"
    assert body["git_execution_request"]["head_branch"] == (
        "fix/sre-oomkilled"
    )
    assert body["git_execution_request"]["target_file"] == (
        "chaos/oomkilled-pod.yaml"
    )
    assert body["git_execution_request"]["commit_message"] == (
        "fix(sre): remediate OOMKilled"
    )
    assert "memory: 64Mi" in (
        body["git_execution_request"]["rendered_yaml"]
    )
    assert body["git_execution_request"]["pr_title"] == (
        "fix(sre): remediate OOMKilled"
    )

    assert body["git_execution_request"]["create_branch"] is True
    assert body["git_execution_request"]["write_file"] is True
    assert body["git_execution_request"]["create_commit"] is True
    assert body["git_execution_request"]["push_branch"] is True
    assert body["git_execution_request"]["create_pr"] is True

    assert body["git_execution_request"]["authorized"] is True
    assert body["git_execution_request"]["performs_write"] is False

    # Git executor dry-run result
    assert body["git_execution_result"] is not None

    assert body["git_execution_result"]["repository"] == (
        "stevvv2005/kubepilot"
    )
    assert body["git_execution_result"]["base_branch"] == "main"
    assert body["git_execution_result"]["head_branch"] == (
        "fix/sre-oomkilled"
    )

    assert body["git_execution_result"]["target_file"] == (
        "chaos/oomkilled-pod.yaml"
    )

    assert body["git_execution_result"]["commit_message"] == (
        "fix(sre): remediate OOMKilled"
    )

    assert body["git_execution_result"]["dry_run"] is True

    assert body["git_execution_result"]["would_create_branch"] is True
    assert body["git_execution_result"]["would_write_file"] is True
    assert body["git_execution_result"]["would_create_commit"] is True
    assert body["git_execution_result"]["would_push_branch"] is True
    assert body["git_execution_result"]["would_create_pr"] is True

    assert body["git_execution_result"]["executed"] is False
    assert body["git_execution_result"]["performs_write"] is False


@patch("agent.webhook.app.analyze_pod")
def test_rejected_approval_does_not_create_execution_result(
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

    assert body["approved_manifest"] is None
    assert body["git_commit_dry_run"] is None
    assert body["git_execution_gateway"] is None
    assert body["git_execution_request"] is None

    # Rejected approval must never reach the executor.
    assert body["git_execution_result"] is None

    assert body["pr_payload"]["ready_to_create"] is False
    assert body["pr_payload"]["writes_git"] is False
    assert body["pr_payload"]["creates_pr"] is False

    assert body["github_pr_gateway"]["allowed"] is False
    assert body["github_pr_gateway"]["ready_to_send"] is False
    assert body["github_pr_gateway"]["performs_write"] is False

    assert body["github_pr_request"]["ready_to_send"] is False
    assert body["github_pr_request"]["performs_write"] is False


@patch("agent.webhook.app.analyze_pod")
def test_approval_github_live_disabled_by_default(
    mock_analyze_pod,
    monkeypatch,
):
    monkeypatch.delenv(
        "KUBEPILOT_GITHUB_LIVE_AUTHORIZED",
        raising=False,
    )

    monkeypatch.delenv(
        "GITHUB_TOKEN",
        raising=False,
    )

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

    def fail_if_called(**kwargs):
        raise AssertionError(
            "SRE GitHub live executor must not be called."
        )

    monkeypatch.setattr(
        webhook_app,
        "execute_sre_github_pr_request",
        fail_if_called,
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

    live = response.json()["github_live_execution"]

    assert live["authorized"] is False
    assert live["gateway"]["allowed"] is False
    assert live["result"] is None


@patch("agent.webhook.app.analyze_pod")
def test_approval_github_live_executes_once(
    mock_analyze_pod,
    monkeypatch,
):
    monkeypatch.setenv(
        "KUBEPILOT_GITHUB_LIVE_AUTHORIZED",
        "true",
    )

    monkeypatch.setenv(
        "GITHUB_TOKEN",
        "test-token",
    )

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

    class FakeGitHubClient:
        def __init__(self, **kwargs):
            pass

    monkeypatch.setattr(
        webhook_app,
        "GitHubRESTClient",
        FakeGitHubClient,
    )

    github_configs = []

    monkeypatch.setattr(
        webhook_app,
        "GitHubRESTConfig",
        lambda **kwargs: (
            github_configs.append(kwargs)
            or SimpleNamespace(**kwargs)
        ),
    )

    calls = {
        "count": 0,
    }

    def fake_execute_sre_github_pr_request(
        **kwargs,
    ):
        calls["count"] += 1

        return SimpleNamespace(
            repository="stevvv2005/kubepilot",
            base_branch="main",
            head_branch="fix/sre-oomkilled",
            target_file="chaos/oomkilled-pod.yaml",
            commit_sha="abc123",
            pr_number=79,
            pr_url=(
                "https://github.com/"
                "stevvv2005/kubepilot/pull/79"
            ),
            executed=True,
            performs_cluster_write=False,
        )

    monkeypatch.setattr(
        webhook_app,
        "execute_sre_github_pr_request",
        fake_execute_sre_github_pr_request,
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
    assert calls["count"] == 1
    assert github_configs == [
        {
            "token": "test-token",
            "branch_prefix": "fix/sre-",
        }
    ]

    live = response.json()["github_live_execution"]

    assert live["authorized"] is True
    assert live["gateway"]["allowed"] is True
    assert live["result"]["executed"] is True
    assert live["result"]["pr_number"] == 79
    assert (
        live["result"]["performs_cluster_write"]
        is False
    )


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

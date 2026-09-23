from types import SimpleNamespace

from fastapi.testclient import TestClient

import agent.webhook.app as webhook_app
from agent.finops_agent.gitops_diff import GitOpsDiffProposal
from agent.finops_agent.live_gitops_pipeline import (
    LiveGitOpsPipelineResult,
)


client = TestClient(webhook_app.app)


def _diff():
    return GitOpsDiffProposal(
        namespace="default",
        workload_name="checkoutservice-abc123",
        workload_type="Pod",
        target_file=(
            "gitops/apps/online-boutique/base/"
            "kubernetes-manifests.yaml"
        ),
        manifest_kind="Deployment",
        manifest_name="checkoutservice",
        container_name="server",
        current_cpu_request="100m",
        proposed_cpu_request="10m",
        current_memory_request="64Mi",
        proposed_memory_request="16Mi",
        estimated_monthly_savings_usd=0.62,
        reason="test",
        confidence="medium",
        requires_human_approval=True,
        writes_file=False,
        writes_git=False,
        auto_apply=False,
    )


def _pipeline():
    return LiveGitOpsPipelineResult(
        source="opencost",
        namespace_filter="default",
        total_workloads=12,
        waste_candidates=1,
        resolved_targets=1,
        gitops_diffs=1,
        diffs=(_diff(),),
        read_only=True,
        performs_write=False,
        writes_file=False,
        writes_git=False,
        requires_human_approval=True,
        auto_apply=False,
    )


def test_finops_approval_endpoint_approved(monkeypatch):
    monkeypatch.setattr(
        webhook_app,
        "generate_live_gitops_pipeline",
        lambda **kwargs: _pipeline(),
    )

    monkeypatch.setattr(
        webhook_app,
        "render_approved_finops_manifest",
        lambda **kwargs: SimpleNamespace(
            target_file=(
                "gitops/apps/online-boutique/base/"
                "kubernetes-manifests.yaml"
            ),
            manifest_kind="Deployment",
            manifest_name="checkoutservice",
            container_name="server",
            approved_cpu_request="50m",
            approved_memory_request="32Mi",
            rendered_yaml="kind: Deployment\n",
            ready_for_commit=True,
            writes_file=False,
            writes_git=False,
        ),
    )

    monkeypatch.setattr(
        webhook_app,
        "build_finops_git_commit_dry_run",
        lambda manifest: SimpleNamespace(
            target_file=manifest.target_file,
            branch_name=(
                "fix/finops-checkoutservice-rightsizing"
            ),
            commit_message=(
                "fix(finops): rightsize checkoutservice"
            ),
            rendered_yaml=manifest.rendered_yaml,
            ready_to_commit=True,
            performs_write=False,
            writes_file=False,
            writes_git=False,
        ),
    )

    monkeypatch.setattr(
        webhook_app,
        "validate_finops_git_execution",
        lambda plan: SimpleNamespace(
            allowed=True,
            reason="safe",
            ready_to_execute=True,
            performs_write=False,
        ),
    )

    monkeypatch.setattr(
        webhook_app,
        "build_finops_git_execution_request",
        lambda **kwargs: SimpleNamespace(
            repository="stevvv2005/kubepilot",
            base_branch="main",
            head_branch=(
                "fix/finops-checkoutservice-rightsizing"
            ),
            target_file=(
                "gitops/apps/online-boutique/base/"
                "kubernetes-manifests.yaml"
            ),
            commit_message=(
                "fix(finops): rightsize checkoutservice"
            ),
            rendered_yaml="kind: Deployment\n",
            pr_title=(
                "fix(finops): rightsize checkoutservice"
            ),
            pr_body="FinOps PR",
            create_branch=True,
            write_file=True,
            create_commit=True,
            push_branch=True,
            create_pr=True,
            authorized=True,
            performs_write=False,
        ),
    )

    monkeypatch.setattr(
        webhook_app,
        "execute_finops_git_request",
        lambda **kwargs: SimpleNamespace(
            repository="stevvv2005/kubepilot",
            base_branch="main",
            head_branch=(
                "fix/finops-checkoutservice-rightsizing"
            ),
            target_file=(
                "gitops/apps/online-boutique/base/"
                "kubernetes-manifests.yaml"
            ),
            commit_message=(
                "fix(finops): rightsize checkoutservice"
            ),
            dry_run=True,
            would_create_branch=True,
            would_write_file=True,
            would_create_commit=True,
            would_push_branch=True,
            would_create_pr=True,
            executed=False,
            performs_write=False,
        ),
    )

    response = client.post(
        "/finops/approvals",
        json={
            "namespace": "default",
            "workload_name": "checkoutservice-abc123",
            "window": "1h",
            "approved": True,
            "approved_cpu_request": "50m",
            "approved_memory_request": "32Mi",
            "reviewer": "medfa",
            "reason": "Conservative approval",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["approval"]["approved"] is True
    assert body["approval"]["approved_cpu_request"] == "50m"
    assert body["approval"]["approved_memory_request"] == "32Mi"

    assert body["approved_manifest"]["ready_for_commit"] is True
    assert body["git_commit_dry_run"]["ready_to_commit"] is True

    assert body["git_execution_gateway"]["allowed"] is True

    assert (
        body["git_execution_request"]["authorized"]
        is True
    )

    result = body["git_execution_result"]

    assert result["dry_run"] is True
    assert result["would_create_branch"] is True
    assert result["would_write_file"] is True
    assert result["would_create_commit"] is True
    assert result["would_push_branch"] is True
    assert result["would_create_pr"] is True
    assert result["executed"] is False
    assert result["performs_write"] is False


def test_finops_approval_endpoint_rejected(monkeypatch):
    monkeypatch.setattr(
        webhook_app,
        "generate_live_gitops_pipeline",
        lambda **kwargs: _pipeline(),
    )

    response = client.post(
        "/finops/approvals",
        json={
            "namespace": "default",
            "workload_name": "checkoutservice-abc123",
            "approved": False,
            "reviewer": "medfa",
            "reason": "Need more historical data",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["approval"]["approved"] is False
    assert body["approval"]["ready_for_render"] is False

    assert body["approved_manifest"] is None
    assert body["git_commit_dry_run"] is None
    assert body["git_execution_gateway"] is None
    assert body["git_execution_request"] is None
    assert body["git_execution_result"] is None


def test_finops_approval_unknown_workload(monkeypatch):
    monkeypatch.setattr(
        webhook_app,
        "generate_live_gitops_pipeline",
        lambda **kwargs: _pipeline(),
    )

    response = client.post(
        "/finops/approvals",
        json={
            "namespace": "default",
            "workload_name": "unknown-service",
            "approved": True,
            "reviewer": "medfa",
            "reason": "test",
        },
    )

    assert response.status_code == 404


def test_finops_approval_opencost_failure(monkeypatch):
    def fail(**kwargs):
        raise RuntimeError(
            "OpenCost unavailable"
        )

    monkeypatch.setattr(
        webhook_app,
        "generate_live_gitops_pipeline",
        fail,
    )

    response = client.post(
        "/finops/approvals",
        json={
            "namespace": "default",
            "workload_name": "checkoutservice",
            "approved": True,
            "reviewer": "medfa",
            "reason": "test",
        },
    )

    assert response.status_code == 503

    assert (
        "OpenCost unavailable"
        in response.json()["detail"]
    )

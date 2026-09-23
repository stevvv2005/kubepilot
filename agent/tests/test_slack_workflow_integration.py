from types import SimpleNamespace

from fastapi.testclient import TestClient

import agent.webhook.app as webhook_app


client = TestClient(webhook_app.app)


def test_sre_alert_includes_slack_dry_run(monkeypatch):
    monkeypatch.setattr(
        webhook_app,
        "resolve_target_file",
        lambda **kwargs: SimpleNamespace(
            namespace="default",
            pod_name="checkoutservice-abc",
            container_name="server",
            target_file="gitops/test.yaml",
            matched=True,
            reason="test",
        ),
    )

    diagnosis = SimpleNamespace(
        incident_type="OOMKilled",
        root_cause="Container exceeded memory limit.",
        recommendation="Review memory limits.",
        confidence="high",
    )

    monkeypatch.setattr(
        webhook_app,
        "analyze_pod",
        lambda **kwargs: SimpleNamespace(
            diagnosis=diagnosis,
            memory_mib=128,
            cpu_millicores=50,
        ),
    )

    monkeypatch.setattr(
        webhook_app,
        "build_remediation_proposal",
        lambda *args, **kwargs: SimpleNamespace(
            incident_type="OOMKilled",
            summary="test",
            proposed_change="test",
            target_file="gitops/test.yaml",
            requires_human_approval=True,
            direct_cluster_write=False,
        ),
    )

    monkeypatch.setattr(
        webhook_app,
        "build_git_change_proposal",
        lambda *args, **kwargs: SimpleNamespace(
            incident_type="OOMKilled",
            target_file="gitops/test.yaml",
            change_type="update",
            description="test",
            requires_human_approval=True,
            apply_directly=False,
        ),
    )

    monkeypatch.setattr(
        webhook_app,
        "build_manifest_diff_proposal",
        lambda **kwargs: SimpleNamespace(
            incident_type="OOMKilled",
            target_file="gitops/test.yaml",
            change_type="update",
            before="128Mi",
            after="256Mi",
            requires_human_approval=True,
            writes_file=False,
        ),
    )

    monkeypatch.setattr(
        webhook_app,
        "build_patch_proposal",
        lambda **kwargs: SimpleNamespace(
            incident_type="OOMKilled",
            target_file="gitops/test.yaml",
            container_name="server",
            field="resources.limits.memory",
            current_value="128Mi",
            proposed_value=None,
            reason="test",
            requires_human_approval=True,
            writes_file=False,
        ),
    )

    monkeypatch.setattr(
        webhook_app,
        "suggest_candidate_value",
        lambda **kwargs: SimpleNamespace(
            incident_type="OOMKilled",
            field="resources.limits.memory",
            current_value="128Mi",
            candidate_value="256Mi",
            reason="test",
            confidence="high",
            requires_human_approval=True,
            auto_apply=False,
        ),
    )

    monkeypatch.setattr(
        webhook_app,
        "build_reviewed_patch_payload",
        lambda **kwargs: SimpleNamespace(
            incident_type="OOMKilled",
            target_file="gitops/test.yaml",
            container_name="server",
            field="resources.limits.memory",
            current_value="128Mi",
            candidate_value="256Mi",
            approved_value=None,
            reason="test",
            confidence="high",
            requires_human_approval=True,
            ready_for_pr=False,
            writes_file=False,
            auto_apply=False,
        ),
    )

    monkeypatch.setattr(
        webhook_app,
        "build_pr_payload",
        lambda **kwargs: SimpleNamespace(
            incident_type="OOMKilled",
            title="test",
            branch_name="fix/test",
            target_file="gitops/test.yaml",
            container_name="server",
            field="resources.limits.memory",
            current_value="128Mi",
            approved_value=None,
            commit_message="test",
            pr_body="test",
            ready_to_create=False,
            writes_git=False,
            creates_pr=False,
        ),
    )

    monkeypatch.setattr(
        webhook_app,
        "validate_pr_payload_for_github",
        lambda **kwargs: SimpleNamespace(
            allowed=False,
            reason="not approved",
            ready_to_send=False,
            performs_write=False,
        ),
    )

    monkeypatch.setattr(
        webhook_app,
        "build_github_pr_request",
        lambda **kwargs: SimpleNamespace(
            repository="stevvv2005/kubepilot",
            base_branch="main",
            head_branch="fix/test",
            title="test",
            body="test",
            target_file="gitops/test.yaml",
            approved_value=None,
            ready_to_send=False,
            performs_write=False,
        ),
    )

    response = client.post(
        "/alerts",
        json={
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "PodOOMKilled",
                        "namespace": "default",
                        "pod": "checkoutservice-abc",
                        "container": "server",
                        "severity": "critical",
                    },
                    "annotations": {},
                }
            ],
        },
    )

    assert response.status_code == 200

    slack = response.json()["slack_notification"]

    assert slack["notification_type"] == "sre"
    assert slack["destination"] == "#kubepilot-alerts"
    assert slack["dry_run"] is True
    assert slack["would_send"] is True
    assert slack["sent"] is False
    assert slack["performs_write"] is False


def test_finops_approval_includes_slack_dry_run(
    monkeypatch,
):
    diff = SimpleNamespace(
        namespace="default",
        workload_name="checkoutservice",
        workload_type="Deployment",
        target_file="gitops/test.yaml",
        manifest_kind="Deployment",
        manifest_name="checkoutservice",
        container_name="server",
        current_cpu_request="100m",
        proposed_cpu_request="10m",
        current_memory_request="64Mi",
        proposed_memory_request="16Mi",
        estimated_monthly_savings_usd=0.62,
        confidence="medium",
        requires_human_approval=True,
        writes_file=False,
        writes_git=False,
        auto_apply=False,
    )

    monkeypatch.setattr(
        webhook_app,
        "generate_live_gitops_pipeline",
        lambda **kwargs: SimpleNamespace(
            source="opencost",
            namespace_filter="default",
            total_workloads=12,
            waste_candidates=1,
            resolved_targets=1,
            gitops_diffs=1,
            diffs=(diff,),
            read_only=True,
            performs_write=False,
        ),
    )

    monkeypatch.setattr(
        webhook_app,
        "apply_finops_approval",
        lambda **kwargs: SimpleNamespace(
            approved=False,
            reviewer="medfa",
            reason="Need more data",
            approved_cpu_request=None,
            approved_memory_request=None,
            ready_for_render=False,
            writes_file=False,
            writes_git=False,
            auto_apply=False,
        ),
    )

    response = client.post(
        "/finops/approvals",
        json={
            "namespace": "default",
            "workload_name": "checkoutservice",
            "window": "1h",
            "approved": False,
            "reviewer": "medfa",
            "reason": "Need more data",
        },
    )

    assert response.status_code == 200

    slack = response.json()["slack_notification"]

    assert slack["notification_type"] == "finops"
    assert slack["destination"] == "#kubepilot-finops"
    assert slack["dry_run"] is True
    assert slack["would_send"] is True
    assert slack["sent"] is False
    assert slack["performs_write"] is False
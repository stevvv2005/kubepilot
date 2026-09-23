from fastapi.testclient import TestClient

import agent.webhook.app as webhook_app
from agent.finops_agent.cost_analysis import FinOpsAnalysis
from agent.finops_agent.finops_report import FinOpsReport
from agent.finops_agent.live_report import LiveFinOpsReport
from types import SimpleNamespace

from agent.finops_agent.live_rightsizing import (
    LiveRightsizingResult,
)
from agent.finops_agent.rightsizing_proposal import (
    RightsizingProposal,
)

client = TestClient(webhook_app.app)


def test_finops_report_endpoint(monkeypatch):
    fake_analysis = FinOpsAnalysis(
        namespace="default",
        workload_name="checkoutservice",
        workload_type="Deployment",
        cpu_utilization_pct=10.0,
        memory_utilization_pct=20.0,
        monthly_cost_usd=20.0,
        waste_detected=True,
        recommendation="Workload appears underutilized.",
        estimated_monthly_savings_usd=5.0,
        confidence="medium",
        requires_human_approval=True,
        auto_apply=False,
    )

    fake_report = FinOpsReport(
        total_workloads=2,
        analyzed_workloads=2,
        waste_candidates=1,
        total_monthly_cost_usd=40.0,
        estimated_monthly_savings_usd=5.0,
        estimated_savings_pct=12.5,
        recommendations=(fake_analysis,),
        requires_human_approval=True,
        auto_apply=False,
    )

    fake_live_report = LiveFinOpsReport(
        source="opencost",
        namespace_filter="default",
        report=fake_report,
        read_only=True,
        performs_write=False,
    )

    def fake_generate_live_finops_report(
        client,
        window="1h",
        namespace=None,
    ):
        return fake_live_report

    monkeypatch.setattr(
        webhook_app,
        "generate_live_finops_report",
        fake_generate_live_finops_report,
    )

    response = client.get(
        "/finops/report",
        params={
            "namespace": "default",
            "window": "1h",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["source"] == "opencost"
    assert body["namespace"] == "default"

    assert body["total_workloads"] == 2
    assert body["analyzed_workloads"] == 2
    assert body["waste_candidates"] == 1

    assert body["total_monthly_cost_usd"] == 40.0

    assert (
        body["estimated_monthly_savings_usd"]
        == 5.0
    )

    assert body["estimated_savings_pct"] == 12.5

    assert body["read_only"] is True
    assert body["performs_write"] is False

    assert (
        body["requires_human_approval"]
        is True
    )

    assert body["auto_apply"] is False

    assert len(body["recommendations"]) == 1

    recommendation = body["recommendations"][0]

    assert (
        recommendation["workload_name"]
        == "checkoutservice"
    )

    assert (
        recommendation["cpu_utilization_pct"]
        == 10.0
    )

    assert (
        recommendation["memory_utilization_pct"]
        == 20.0
    )

    assert recommendation["auto_apply"] is False


def test_finops_report_endpoint_without_namespace(
    monkeypatch,
):
    fake_report = FinOpsReport(
        total_workloads=0,
        analyzed_workloads=0,
        waste_candidates=0,
        total_monthly_cost_usd=0.0,
        estimated_monthly_savings_usd=0.0,
        estimated_savings_pct=0.0,
        recommendations=(),
        requires_human_approval=True,
        auto_apply=False,
    )

    fake_live_report = LiveFinOpsReport(
        source="opencost",
        namespace_filter=None,
        report=fake_report,
        read_only=True,
        performs_write=False,
    )

    def fake_generate_live_finops_report(
        client,
        window="1h",
        namespace=None,
    ):
        assert namespace is None

        return fake_live_report

    monkeypatch.setattr(
        webhook_app,
        "generate_live_finops_report",
        fake_generate_live_finops_report,
    )

    response = client.get(
        "/finops/report",
    )

    assert response.status_code == 200

    body = response.json()

    assert body["namespace"] is None
    assert body["total_workloads"] == 0
    assert body["recommendations"] == []


def test_finops_report_endpoint_returns_503(
    monkeypatch,
):
    def fake_generate_live_finops_report(
        client,
        window="1h",
        namespace=None,
    ):
        raise RuntimeError(
            "OpenCost unavailable"
        )

    monkeypatch.setattr(
        webhook_app,
        "generate_live_finops_report",
        fake_generate_live_finops_report,
    )

    response = client.get(
        "/finops/report",
    )

    assert response.status_code == 503

    body = response.json()

    assert (
        "OpenCost unavailable"
        in body["detail"]
    )
def _fake_rightsizing_result():
    proposal = RightsizingProposal(
        namespace="default",
        workload_name="checkoutservice",
        workload_type="Deployment",
        current_cpu_request_cores=0.5,
        current_memory_request_mib=512.0,
        suggested_cpu_request_cores=0.2,
        suggested_memory_request_mib=256.0,
        cpu_utilization_pct=10.0,
        memory_utilization_pct=20.0,
        current_monthly_cost_usd=20.0,
        estimated_monthly_savings_usd=5.0,
        reason=(
            "Workload is underutilized."
        ),
        confidence="medium",
        requires_human_approval=True,
        auto_apply=False,
        performs_write=False,
    )

    return LiveRightsizingResult(
        source="opencost",
        namespace_filter="default",
        total_workloads=1,
        waste_candidates=1,
        proposals=(proposal,),
        read_only=True,
        performs_write=False,
        requires_human_approval=True,
        auto_apply=False,
    )


def test_finops_rightsizing_includes_llm_analysis(
    monkeypatch,
):
    fake_result = _fake_rightsizing_result()

    def fake_generate_live_rightsizing(
        client,
        window="1h",
        namespace=None,
    ):
        return fake_result

    fake_llm_result = SimpleNamespace(
        response=SimpleNamespace(
            provider="mock",
            model="kubepilot-mock-v1",
            content=(
                "FinOps mock analysis with "
                "GitOps recommendation."
            ),
            rag_context_used=True,
            sources=(
                "agent/knowledge/"
                "finops_runbooks.md",
            ),
        ),
        requires_human_approval=True,
        allows_direct_cluster_write=False,
        external_request_performed=False,
        performs_write=False,
    )

    def fake_run_llm_workflow(
        **kwargs,
    ):
        return fake_llm_result

    monkeypatch.setattr(
        webhook_app,
        "generate_live_rightsizing",
        fake_generate_live_rightsizing,
    )

    monkeypatch.setattr(
        webhook_app,
        "run_llm_workflow",
        fake_run_llm_workflow,
    )

    response = client.get(
        "/finops/rightsizing",
        params={
            "namespace": "default",
            "window": "1h",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["source"] == "opencost"
    assert body["waste_candidates"] == 1

    assert (
        body["llm_status"]["available"]
        is True
    )

    assert body["llm_status"]["error"] is None

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

    assert len(body["proposals"]) == 1


def test_finops_rightsizing_llm_failure_is_non_blocking(
    monkeypatch,
):
    fake_result = _fake_rightsizing_result()

    def fake_generate_live_rightsizing(
        client,
        window="1h",
        namespace=None,
    ):
        return fake_result

    def fake_run_llm_workflow(
        **kwargs,
    ):
        raise RuntimeError(
            "Simulated FinOps LLM failure"
        )

    monkeypatch.setattr(
        webhook_app,
        "generate_live_rightsizing",
        fake_generate_live_rightsizing,
    )

    monkeypatch.setattr(
        webhook_app,
        "run_llm_workflow",
        fake_run_llm_workflow,
    )

    response = client.get(
        "/finops/rightsizing",
        params={
            "namespace": "default",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["waste_candidates"] == 1

    assert body["llm_analysis"] is None

    assert (
        body["llm_status"]["available"]
        is False
    )

    assert (
        "Simulated FinOps LLM failure"
        in body["llm_status"]["error"]
    )

    assert (
        body["llm_status"]["non_blocking"]
        is True
    )

    assert len(body["proposals"]) == 1


def test_finops_rightsizing_without_proposals_skips_llm(
    monkeypatch,
):
    fake_result = LiveRightsizingResult(
        source="opencost",
        namespace_filter="default",
        total_workloads=1,
        waste_candidates=0,
        proposals=tuple(),
        read_only=True,
        performs_write=False,
        requires_human_approval=True,
        auto_apply=False,
    )

    def fake_generate_live_rightsizing(
        client,
        window="1h",
        namespace=None,
    ):
        return fake_result

    def fail_if_called(
        **kwargs,
    ):
        raise AssertionError(
            "LLM workflow should not be called "
            "when there are no proposals."
        )

    monkeypatch.setattr(
        webhook_app,
        "generate_live_rightsizing",
        fake_generate_live_rightsizing,
    )

    monkeypatch.setattr(
        webhook_app,
        "run_llm_workflow",
        fail_if_called,
    )

    response = client.get(
        "/finops/rightsizing",
        params={
            "namespace": "default",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["waste_candidates"] == 0
    assert body["proposals"] == []

    assert body["llm_analysis"] is None

    assert (
        body["llm_status"]["available"]
        is False
    )

    assert body["llm_status"]["error"] is None

    assert (
        body["llm_status"]["non_blocking"]
        is True
    )
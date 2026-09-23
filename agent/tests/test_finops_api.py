from fastapi.testclient import TestClient

import agent.webhook.app as webhook_app
from agent.finops_agent.cost_analysis import FinOpsAnalysis
from agent.finops_agent.finops_report import FinOpsReport
from agent.finops_agent.live_report import LiveFinOpsReport


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

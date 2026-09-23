from fastapi.testclient import TestClient

import agent.webhook.app as webhook_app
from agent.finops_agent.live_rightsizing import (
    LiveRightsizingResult,
)
from agent.finops_agent.rightsizing_proposal import (
    RightsizingProposal,
)


client = TestClient(webhook_app.app)


def test_finops_rightsizing_endpoint(monkeypatch):
    fake_proposal = RightsizingProposal(
        namespace="default",
        workload_name="checkoutservice",
        workload_type="Deployment",
        current_cpu_request_cores=0.1,
        current_memory_request_mib=64.0,
        suggested_cpu_request_cores=0.02,
        suggested_memory_request_mib=16.0,
        cpu_utilization_pct=10.0,
        memory_utilization_pct=12.5,
        current_monthly_cost_usd=2.47,
        estimated_monthly_savings_usd=0.62,
        reason="Workload is underutilized.",
        confidence="medium",
        requires_human_approval=True,
        auto_apply=False,
        performs_write=False,
    )

    fake_result = LiveRightsizingResult(
        source="opencost",
        namespace_filter="default",
        total_workloads=12,
        waste_candidates=1,
        proposals=(fake_proposal,),
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

    monkeypatch.setattr(
        webhook_app,
        "generate_live_rightsizing",
        fake_generate_live_rightsizing,
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
    assert body["namespace"] == "default"
    assert body["total_workloads"] == 12
    assert body["waste_candidates"] == 1

    assert body["read_only"] is True
    assert body["performs_write"] is False
    assert body["requires_human_approval"] is True
    assert body["auto_apply"] is False

    assert len(body["proposals"]) == 1

    proposal = body["proposals"][0]

    assert proposal["workload_name"] == "checkoutservice"
    assert proposal["current_cpu_request_cores"] == 0.1
    assert proposal["suggested_cpu_request_cores"] == 0.02
    assert proposal["current_memory_request_mib"] == 64.0
    assert proposal["suggested_memory_request_mib"] == 16.0

    assert proposal["requires_human_approval"] is True
    assert proposal["auto_apply"] is False
    assert proposal["performs_write"] is False


def test_finops_rightsizing_endpoint_without_namespace(
    monkeypatch,
):
    fake_result = LiveRightsizingResult(
        source="opencost",
        namespace_filter=None,
        total_workloads=0,
        waste_candidates=0,
        proposals=(),
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
        assert namespace is None
        return fake_result

    monkeypatch.setattr(
        webhook_app,
        "generate_live_rightsizing",
        fake_generate_live_rightsizing,
    )

    response = client.get(
        "/finops/rightsizing",
    )

    assert response.status_code == 200

    body = response.json()

    assert body["namespace"] is None
    assert body["total_workloads"] == 0
    assert body["waste_candidates"] == 0
    assert body["proposals"] == []


def test_finops_rightsizing_endpoint_returns_503(
    monkeypatch,
):
    def fake_generate_live_rightsizing(
        client,
        window="1h",
        namespace=None,
    ):
        raise RuntimeError(
            "OpenCost unavailable"
        )

    monkeypatch.setattr(
        webhook_app,
        "generate_live_rightsizing",
        fake_generate_live_rightsizing,
    )

    response = client.get(
        "/finops/rightsizing",
    )

    assert response.status_code == 503

    assert (
        "OpenCost unavailable"
        in response.json()["detail"]
    )
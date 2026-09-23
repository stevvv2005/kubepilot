import pytest

from agent.finops_agent.cost_analysis import (
    WorkloadCostSnapshot,
    analyze_workload_cost,
)
from agent.finops_agent.rightsizing_proposal import (
    build_rightsizing_proposal,
)


def test_build_rightsizing_proposal_for_underutilized_workload():
    snapshot = WorkloadCostSnapshot(
        namespace="default",
        workload_name="checkoutservice",
        workload_type="Deployment",
        cpu_request_cores=1.0,
        cpu_usage_cores=0.2,
        memory_request_mib=512.0,
        memory_usage_mib=100.0,
        monthly_cost_usd=40.0,
    )

    analysis = analyze_workload_cost(
        snapshot,
    )

    proposal = build_rightsizing_proposal(
        snapshot=snapshot,
        analysis=analysis,
    )

    assert proposal.namespace == "default"
    assert proposal.workload_name == "checkoutservice"

    assert proposal.current_cpu_request_cores == 1.0
    assert proposal.current_memory_request_mib == 512.0

    assert proposal.suggested_cpu_request_cores == 0.3
    assert proposal.suggested_memory_request_mib == 150.0

    assert proposal.requires_human_approval is True
    assert proposal.auto_apply is False
    assert proposal.performs_write is False


def test_no_proposal_when_workload_is_not_underutilized():
    snapshot = WorkloadCostSnapshot(
        namespace="default",
        workload_name="cartservice",
        workload_type="Deployment",
        cpu_request_cores=1.0,
        cpu_usage_cores=0.8,
        memory_request_mib=512.0,
        memory_usage_mib=400.0,
        monthly_cost_usd=40.0,
    )

    analysis = analyze_workload_cost(
        snapshot,
    )

    proposal = build_rightsizing_proposal(
        snapshot=snapshot,
        analysis=analysis,
    )

    assert proposal.suggested_cpu_request_cores is None
    assert proposal.suggested_memory_request_mib is None

    assert proposal.auto_apply is False
    assert proposal.performs_write is False


def test_low_usage_keeps_minimum_cpu_request():
    snapshot = WorkloadCostSnapshot(
        namespace="default",
        workload_name="tiny-service",
        workload_type="Deployment",
        cpu_request_cores=0.1,
        cpu_usage_cores=0.001,
        memory_request_mib=64.0,
        memory_usage_mib=8.0,
        monthly_cost_usd=5.0,
    )

    analysis = analyze_workload_cost(
        snapshot,
    )

    proposal = build_rightsizing_proposal(
        snapshot=snapshot,
        analysis=analysis,
    )

    assert proposal.suggested_cpu_request_cores == 0.01
    assert proposal.suggested_memory_request_mib == 16.0


def test_missing_usage_returns_no_suggested_value():
    snapshot = WorkloadCostSnapshot(
        namespace="default",
        workload_name="unknown-usage",
        workload_type="Deployment",
        cpu_request_cores=1.0,
        cpu_usage_cores=0.0,
        memory_request_mib=512.0,
        memory_usage_mib=0.0,
        monthly_cost_usd=20.0,
    )

    analysis = analyze_workload_cost(
        snapshot,
    )

    proposal = build_rightsizing_proposal(
        snapshot=snapshot,
        analysis=analysis,
    )

    assert proposal.suggested_cpu_request_cores is None
    assert proposal.suggested_memory_request_mib is None

    assert proposal.confidence == "low"


def test_snapshot_and_analysis_namespace_must_match():
    snapshot = WorkloadCostSnapshot(
        namespace="default",
        workload_name="frontend",
        workload_type="Deployment",
        cpu_request_cores=1.0,
        cpu_usage_cores=0.1,
        memory_request_mib=100.0,
        memory_usage_mib=10.0,
        monthly_cost_usd=10.0,
    )

    analysis = analyze_workload_cost(
        snapshot,
    )

    different_snapshot = WorkloadCostSnapshot(
        namespace="other",
        workload_name="frontend",
        workload_type="Deployment",
        cpu_request_cores=1.0,
        cpu_usage_cores=0.1,
        memory_request_mib=100.0,
        memory_usage_mib=10.0,
        monthly_cost_usd=10.0,
    )

    with pytest.raises(
        ValueError,
        match="namespace do not match",
    ):
        build_rightsizing_proposal(
            snapshot=different_snapshot,
            analysis=analysis,
        )


def test_snapshot_and_analysis_workload_must_match():
    snapshot = WorkloadCostSnapshot(
        namespace="default",
        workload_name="frontend",
        workload_type="Deployment",
        cpu_request_cores=1.0,
        cpu_usage_cores=0.1,
        memory_request_mib=100.0,
        memory_usage_mib=10.0,
        monthly_cost_usd=10.0,
    )

    analysis = analyze_workload_cost(
        snapshot,
    )

    different_snapshot = WorkloadCostSnapshot(
        namespace="default",
        workload_name="other-service",
        workload_type="Deployment",
        cpu_request_cores=1.0,
        cpu_usage_cores=0.1,
        memory_request_mib=100.0,
        memory_usage_mib=10.0,
        monthly_cost_usd=10.0,
    )

    with pytest.raises(
        ValueError,
        match="workload do not match",
    ):
        build_rightsizing_proposal(
            snapshot=different_snapshot,
            analysis=analysis,
        )
        
import pytest

from agent.finops_agent.cost_analysis import (
    WorkloadCostSnapshot,
    analyze_workload_cost,
)


def test_underutilized_workload_detects_waste():
    snapshot = WorkloadCostSnapshot(
        namespace="default",
        workload_name="checkoutservice",
        workload_type="Deployment",
        cpu_request_cores=1.0,
        cpu_usage_cores=0.20,
        memory_request_mib=512.0,
        memory_usage_mib=100.0,
        monthly_cost_usd=40.0,
    )

    analysis = analyze_workload_cost(snapshot)

    assert analysis.cpu_utilization_pct == 20.0
    assert analysis.memory_utilization_pct == 19.53

    assert analysis.waste_detected is True
    assert analysis.estimated_monthly_savings_usd == 10.0

    assert analysis.confidence == "medium"
    assert analysis.requires_human_approval is True
    assert analysis.auto_apply is False


def test_reasonably_used_workload_does_not_detect_waste():
    snapshot = WorkloadCostSnapshot(
        namespace="default",
        workload_name="frontend",
        workload_type="Deployment",
        cpu_request_cores=1.0,
        cpu_usage_cores=0.70,
        memory_request_mib=512.0,
        memory_usage_mib=350.0,
        monthly_cost_usd=50.0,
    )

    analysis = analyze_workload_cost(snapshot)

    assert analysis.waste_detected is False
    assert analysis.estimated_monthly_savings_usd == 0.0
    assert analysis.auto_apply is False


def test_missing_cpu_request_returns_low_confidence():
    snapshot = WorkloadCostSnapshot(
        namespace="default",
        workload_name="frontend",
        workload_type="Deployment",
        cpu_request_cores=0.0,
        cpu_usage_cores=0.10,
        memory_request_mib=512.0,
        memory_usage_mib=100.0,
        monthly_cost_usd=20.0,
    )

    analysis = analyze_workload_cost(snapshot)

    assert analysis.cpu_utilization_pct is None
    assert analysis.waste_detected is False
    assert analysis.estimated_monthly_savings_usd is None
    assert analysis.confidence == "low"


def test_negative_values_are_rejected():
    snapshot = WorkloadCostSnapshot(
        namespace="default",
        workload_name="frontend",
        workload_type="Deployment",
        cpu_request_cores=-1.0,
        cpu_usage_cores=0.10,
        memory_request_mib=512.0,
        memory_usage_mib=100.0,
        monthly_cost_usd=20.0,
    )

    with pytest.raises(
        ValueError,
        match="cannot be negative",
    ):
        analyze_workload_cost(snapshot)


def test_finops_analysis_never_auto_applies():
    snapshot = WorkloadCostSnapshot(
        namespace="default",
        workload_name="checkoutservice",
        workload_type="Deployment",
        cpu_request_cores=2.0,
        cpu_usage_cores=0.20,
        memory_request_mib=1024.0,
        memory_usage_mib=200.0,
        monthly_cost_usd=100.0,
    )

    analysis = analyze_workload_cost(snapshot)

    assert analysis.requires_human_approval is True
    assert analysis.auto_apply is False

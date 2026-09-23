from agent.finops_agent.cost_analysis import (
    WorkloadCostSnapshot,
)
from agent.finops_agent.finops_report import (
    build_finops_report,
)


def test_build_finops_report():
    snapshots = [
        WorkloadCostSnapshot(
            namespace="default",
            workload_name="checkoutservice",
            workload_type="Deployment",
            cpu_request_cores=1.0,
            cpu_usage_cores=0.2,
            memory_request_mib=512.0,
            memory_usage_mib=100.0,
            monthly_cost_usd=40.0,
        ),
        WorkloadCostSnapshot(
            namespace="default",
            workload_name="cartservice",
            workload_type="Deployment",
            cpu_request_cores=1.0,
            cpu_usage_cores=0.7,
            memory_request_mib=512.0,
            memory_usage_mib=350.0,
            monthly_cost_usd=60.0,
        ),
    ]

    report = build_finops_report(
        snapshots,
    )

    assert report.total_workloads == 2
    assert report.analyzed_workloads == 2

    assert report.waste_candidates == 1

    assert (
        report.total_monthly_cost_usd
        == 100.0
    )

    assert (
        report.estimated_monthly_savings_usd
        == 10.0
    )

    assert (
        report.estimated_savings_pct
        == 10.0
    )

    assert len(
        report.recommendations
    ) == 1

    assert (
        report.recommendations[0].workload_name
        == "checkoutservice"
    )

    assert (
        report.requires_human_approval
        is True
    )

    assert report.auto_apply is False


def test_report_with_multiple_waste_candidates():
    snapshots = [
        WorkloadCostSnapshot(
            namespace="default",
            workload_name="frontend",
            workload_type="Deployment",
            cpu_request_cores=1.0,
            cpu_usage_cores=0.1,
            memory_request_mib=100.0,
            memory_usage_mib=10.0,
            monthly_cost_usd=20.0,
        ),
        WorkloadCostSnapshot(
            namespace="default",
            workload_name="shippingservice",
            workload_type="Deployment",
            cpu_request_cores=1.0,
            cpu_usage_cores=0.2,
            memory_request_mib=100.0,
            memory_usage_mib=20.0,
            monthly_cost_usd=40.0,
        ),
    ]

    report = build_finops_report(
        snapshots,
    )

    assert report.total_workloads == 2
    assert report.waste_candidates == 2

    # 25% of $20 = $5
    # 25% of $40 = $10
    assert (
        report.estimated_monthly_savings_usd
        == 15.0
    )

    assert (
        report.total_monthly_cost_usd
        == 60.0
    )

    assert (
        report.estimated_savings_pct
        == 25.0
    )


def test_report_with_no_waste():
    snapshots = [
        WorkloadCostSnapshot(
            namespace="default",
            workload_name="cartservice",
            workload_type="Deployment",
            cpu_request_cores=1.0,
            cpu_usage_cores=0.8,
            memory_request_mib=100.0,
            memory_usage_mib=80.0,
            monthly_cost_usd=50.0,
        )
    ]

    report = build_finops_report(
        snapshots,
    )

    assert report.total_workloads == 1

    assert (
        report.waste_candidates
        == 0
    )

    assert (
        report.estimated_monthly_savings_usd
        == 0.0
    )

    assert (
        report.estimated_savings_pct
        == 0.0
    )

    assert (
        report.recommendations
        == ()
    )


def test_report_with_missing_request_data():
    snapshots = [
        WorkloadCostSnapshot(
            namespace="argocd",
            workload_name="argocd-server",
            workload_type="Pod",
            cpu_request_cores=0.0,
            cpu_usage_cores=0.01,
            memory_request_mib=0.0,
            memory_usage_mib=50.0,
            monthly_cost_usd=0.0,
        )
    ]

    report = build_finops_report(
        snapshots,
    )

    assert report.total_workloads == 1
    assert report.analyzed_workloads == 1

    assert (
        report.waste_candidates
        == 0
    )

    assert (
        report.total_monthly_cost_usd
        == 0.0
    )

    assert (
        report.estimated_monthly_savings_usd
        == 0.0
    )

    assert (
        report.estimated_savings_pct
        == 0.0
    )


def test_empty_report():
    report = build_finops_report(
        [],
    )

    assert report.total_workloads == 0
    assert report.analyzed_workloads == 0
    assert report.waste_candidates == 0

    assert (
        report.total_monthly_cost_usd
        == 0.0
    )

    assert (
        report.estimated_monthly_savings_usd
        == 0.0
    )

    assert (
        report.estimated_savings_pct
        == 0.0
    )

    assert report.recommendations == ()

    assert (
        report.requires_human_approval
        is True
    )

    assert report.auto_apply is False


def test_report_recommendations_only_include_waste():
    snapshots = [
        WorkloadCostSnapshot(
            namespace="default",
            workload_name="frontend",
            workload_type="Deployment",
            cpu_request_cores=1.0,
            cpu_usage_cores=0.1,
            memory_request_mib=100.0,
            memory_usage_mib=10.0,
            monthly_cost_usd=20.0,
        ),
        WorkloadCostSnapshot(
            namespace="default",
            workload_name="adservice",
            workload_type="Deployment",
            cpu_request_cores=1.0,
            cpu_usage_cores=0.1,
            memory_request_mib=100.0,
            memory_usage_mib=70.0,
            monthly_cost_usd=30.0,
        ),
    ]

    report = build_finops_report(
        snapshots,
    )

    names = {
        recommendation.workload_name
        for recommendation
        in report.recommendations
    }

    assert names == {
        "frontend",
    }

    assert all(
        recommendation.waste_detected
        for recommendation
        in report.recommendations
    )

    assert all(
        recommendation.auto_apply is False
        for recommendation
        in report.recommendations
    )

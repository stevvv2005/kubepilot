from agent.finops_agent.live_report import (
    generate_live_finops_report,
)
from agent.finops_agent.opencost_client import (
    OpenCostClient,
)


class FakeOpenCostClient(OpenCostClient):
    def get_allocations(
        self,
        window: str = "1h",
        aggregate: str = "namespace,pod",
    ):
        return {
            "data": [
                {
                    "default/frontend": {
                        "properties": {
                            "namespace": "default",
                            "pod": "frontend-123",
                            "controller": "frontend",
                            "controllerKind": "Deployment",
                        },
                        "minutes": 60,
                        "cpuCoreRequestAverage": 1.0,
                        "cpuCoreUsageAverage": 0.1,
                        "ramByteRequestAverage": 104857600,
                        "ramByteUsageAverage": 10485760,
                        "cpuCost": 0.01,
                        "ramCost": 0.01,
                    },
                    "default/cart": {
                        "properties": {
                            "namespace": "default",
                            "pod": "cart-123",
                            "controller": "cartservice",
                            "controllerKind": "Deployment",
                        },
                        "minutes": 60,
                        "cpuCoreRequestAverage": 1.0,
                        "cpuCoreUsageAverage": 0.8,
                        "ramByteRequestAverage": 104857600,
                        "ramByteUsageAverage": 83886080,
                        "cpuCost": 0.02,
                        "ramCost": 0.02,
                    },
                    "monitoring/prometheus": {
                        "properties": {
                            "namespace": "monitoring",
                            "pod": "prometheus-0",
                        },
                        "minutes": 60,
                        "cpuCoreRequestAverage": 1.0,
                        "cpuCoreUsageAverage": 0.2,
                        "ramByteRequestAverage": 1073741824,
                        "ramByteUsageAverage": 214748364,
                        "cpuCost": 0.03,
                        "ramCost": 0.03,
                    },
                }
            ]
        }


def test_generate_live_finops_report():
    client = FakeOpenCostClient()

    result = generate_live_finops_report(
        client=client,
        window="1h",
    )

    assert result.source == "opencost"
    assert result.namespace_filter is None

    assert result.report.total_workloads == 3
    assert result.report.analyzed_workloads == 3

    assert result.report.waste_candidates == 2

    assert result.read_only is True
    assert result.performs_write is False


def test_generate_live_finops_report_with_namespace_filter():
    client = FakeOpenCostClient()

    result = generate_live_finops_report(
        client=client,
        window="1h",
        namespace="default",
    )

    assert result.namespace_filter == "default"

    assert result.report.total_workloads == 2
    assert result.report.analyzed_workloads == 2

    assert result.report.waste_candidates == 1


def test_live_report_preserves_safety_flags():
    client = FakeOpenCostClient()

    result = generate_live_finops_report(
        client=client,
    )

    assert result.read_only is True
    assert result.performs_write is False

    assert (
        result.report.requires_human_approval
        is True
    )

    assert result.report.auto_apply is False

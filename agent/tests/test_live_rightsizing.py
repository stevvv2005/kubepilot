from agent.finops_agent.live_rightsizing import (
    generate_live_rightsizing,
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
                    "default/checkoutservice": {
                        "properties": {
                            "namespace": "default",
                            "controller": "checkoutservice",
                            "controllerKind": "Deployment",
                            "pod": "checkoutservice-123",
                        },
                        "minutes": 60,
                        "cpuCoreRequestAverage": 0.1,
                        "cpuCoreUsageAverage": 0.01,
                        "ramByteRequestAverage": 67108864,
                        "ramByteUsageAverage": 8388608,
                        "cpuCost": 0.002,
                        "ramCost": 0.001,
                    },
                    "default/cartservice": {
                        "properties": {
                            "namespace": "default",
                            "controller": "cartservice",
                            "controllerKind": "Deployment",
                            "pod": "cartservice-123",
                        },
                        "minutes": 60,
                        "cpuCoreRequestAverage": 0.2,
                        "cpuCoreUsageAverage": 0.1,
                        "ramByteRequestAverage": 67108864,
                        "ramByteUsageAverage": 58720256,
                        "cpuCost": 0.003,
                        "ramCost": 0.002,
                    },
                    "monitoring/prometheus": {
                        "properties": {
                            "namespace": "monitoring",
                            "pod": "prometheus-0",
                        },
                        "minutes": 60,
                        "cpuCoreRequestAverage": 1.0,
                        "cpuCoreUsageAverage": 0.1,
                        "ramByteRequestAverage": 1073741824,
                        "ramByteUsageAverage": 107374182,
                        "cpuCost": 0.03,
                        "ramCost": 0.02,
                    },
                }
            ]
        }


def test_generate_live_rightsizing():
    client = FakeOpenCostClient()

    result = generate_live_rightsizing(
        client=client,
        window="1h",
    )

    assert result.source == "opencost"
    assert result.namespace_filter is None

    assert result.total_workloads == 3

    # checkoutservice + prometheus
    assert result.waste_candidates == 2
    assert len(result.proposals) == 2

    assert result.read_only is True
    assert result.performs_write is False

    assert (
        result.requires_human_approval
        is True
    )

    assert result.auto_apply is False


def test_generate_live_rightsizing_with_namespace():
    client = FakeOpenCostClient()

    result = generate_live_rightsizing(
        client=client,
        window="1h",
        namespace="default",
    )

    assert result.namespace_filter == "default"

    assert result.total_workloads == 2

    # checkoutservice is underutilized.
    # cartservice is not.
    assert result.waste_candidates == 1

    assert len(result.proposals) == 1

    proposal = result.proposals[0]

    assert (
        proposal.workload_name
        == "checkoutservice"
    )

    assert (
        proposal.current_cpu_request_cores
        == 0.1
    )

    assert (
        proposal.current_memory_request_mib
        == 64.0
    )

    assert (
        proposal.suggested_cpu_request_cores
        == 0.02
    )

    assert (
        proposal.suggested_memory_request_mib
        == 16.0
    )


def test_live_rightsizing_only_returns_waste_candidates():
    client = FakeOpenCostClient()

    result = generate_live_rightsizing(
        client=client,
        namespace="default",
    )

    names = {
        proposal.workload_name
        for proposal in result.proposals
    }

    assert names == {
        "checkoutservice",
    }


def test_live_rightsizing_preserves_safety_flags():
    client = FakeOpenCostClient()

    result = generate_live_rightsizing(
        client=client,
        namespace="default",
    )

    assert result.read_only is True
    assert result.performs_write is False

    assert (
        result.requires_human_approval
        is True
    )

    assert result.auto_apply is False

    assert all(
        proposal.requires_human_approval
        for proposal in result.proposals
    )

    assert all(
        proposal.auto_apply is False
        for proposal in result.proposals
    )

    assert all(
        proposal.performs_write is False
        for proposal in result.proposals
    )


def test_empty_namespace_returns_empty_proposals():
    client = FakeOpenCostClient()

    result = generate_live_rightsizing(
        client=client,
        namespace="does-not-exist",
    )

    assert result.total_workloads == 0
    assert result.waste_candidates == 0
    assert result.proposals == ()
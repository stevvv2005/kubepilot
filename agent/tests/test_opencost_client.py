from agent.finops_agent.opencost_client import (
    allocations_to_snapshots,
)


def test_convert_opencost_allocation_to_snapshot():
    payload = {
        "data": [
            {
                "default/frontend": {
                    "name": "default/frontend",
                    "properties": {
                        "namespace": "default",
                        "pod": "frontend-123",
                        "controller": "frontend",
                        "controllerKind": "Deployment",
                    },
                    "cpuCoreRequestAverage": 1.0,
                    "cpuCoreUsageAverage": 0.2,
                    "ramBytesRequestAverage": 536870912,
                    "ramBytesUsageAverage": 104857600,
                    "cpuCost": 0.01,
                    "ramCost": 0.005,
                }
            }
        ]
    }

    snapshots = allocations_to_snapshots(
        payload,
    )

    assert len(snapshots) == 1

    snapshot = snapshots[0]

    assert snapshot.namespace == "default"
    assert snapshot.workload_name == "frontend"
    assert snapshot.workload_type == "Deployment"

    assert snapshot.cpu_request_cores == 1.0
    assert snapshot.cpu_usage_cores == 0.2

    assert snapshot.memory_request_mib == 512.0
    assert snapshot.memory_usage_mib == 100.0

    assert snapshot.monthly_cost_usd == 10.8


def test_missing_optional_values_default_to_zero():
    payload = {
        "data": [
            {
                "default/test": {
                    "name": "default/test",
                    "properties": {
                        "namespace": "default",
                        "pod": "test-pod",
                    },
                }
            }
        ]
    }

    snapshots = allocations_to_snapshots(
        payload,
    )

    snapshot = snapshots[0]

    assert snapshot.cpu_request_cores == 0.0
    assert snapshot.cpu_usage_cores == 0.0
    assert snapshot.memory_request_mib == 0.0
    assert snapshot.memory_usage_mib == 0.0
    assert snapshot.monthly_cost_usd == 0.0


def test_controller_is_preferred_as_workload_name():
    payload = {
        "data": [
            {
                "default/checkout": {
                    "properties": {
                        "namespace": "default",
                        "pod": "checkout-abc",
                        "controller": "checkoutservice",
                        "controllerKind": "Deployment",
                    },
                    "cpuCoreRequestAverage": 0.5,
                    "cpuCoreUsageAverage": 0.1,
                    "ramBytesRequestAverage": 268435456,
                    "ramBytesUsageAverage": 67108864,
                    "cpuCost": 0.02,
                    "ramCost": 0.01,
                }
            }
        ]
    }

    snapshots = allocations_to_snapshots(
        payload,
    )

    assert snapshots[0].workload_name == "checkoutservice"
    assert snapshots[0].workload_type == "Deployment"


def test_invalid_data_shape_is_rejected():
    payload = {
        "data": {
            "not": "a list",
        }
    }

    try:
        allocations_to_snapshots(
            payload,
        )

        assert False

    except ValueError as exc:
        assert "does not contain a data list" in str(exc)


def test_multiple_allocations_are_converted():
    payload = {
        "data": [
            {
                "default/frontend": {
                    "properties": {
                        "namespace": "default",
                        "controller": "frontend",
                        "controllerKind": "Deployment",
                    },
                    "cpuCoreRequestAverage": 1.0,
                    "cpuCoreUsageAverage": 0.4,
                    "ramBytesRequestAverage": 536870912,
                    "ramBytesUsageAverage": 268435456,
                    "cpuCost": 0.01,
                    "ramCost": 0.01,
                },
                "default/cart": {
                    "properties": {
                        "namespace": "default",
                        "controller": "cartservice",
                        "controllerKind": "Deployment",
                    },
                    "cpuCoreRequestAverage": 0.5,
                    "cpuCoreUsageAverage": 0.1,
                    "ramBytesRequestAverage": 268435456,
                    "ramBytesUsageAverage": 67108864,
                    "cpuCost": 0.005,
                    "ramCost": 0.005,
                },
            }
        ]
    }

    snapshots = allocations_to_snapshots(
        payload,
    )

    assert len(snapshots) == 2

    names = {
        snapshot.workload_name
        for snapshot in snapshots
    }

    assert names == {
        "frontend",
        "cartservice",
    }

import pytest

from agent.finops_agent.opencost_client import (
    _estimate_monthly_cost,
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
                    "minutes": 60,
                    "cpuCoreRequestAverage": 1.0,
                    "cpuCoreUsageAverage": 0.2,
                    "ramByteRequestAverage": 536870912,
                    "ramByteUsageAverage": 104857600,
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

    assert (
        snapshot.workload_name
        == "frontend"
    )

    assert (
        snapshot.workload_type
        == "Deployment"
    )

    assert (
        snapshot.cpu_request_cores
        == 1.0
    )

    assert (
        snapshot.cpu_usage_cores
        == 0.2
    )

    assert (
        snapshot.memory_request_mib
        == 512.0
    )

    assert (
        snapshot.memory_usage_mib
        == 100.0
    )

    # $0.015 observed during exactly one hour.
    #
    # 0.015 * 24 * 30 = $10.80/month
    assert (
        snapshot.monthly_cost_usd
        == 10.8
    )


def test_realistic_half_hour_window_is_normalized():
    allocation = {
        "minutes": 30,
        "cpuCost": 0.00156,
        "ramCost": 0.00013,
    }

    monthly_cost = _estimate_monthly_cost(
        allocation,
    )

    # Cost observed for 30 minutes:
    # 0.00169
    #
    # Hourly:
    # 0.00338
    #
    # Monthly:
    # 0.00338 * 24 * 30
    # = 2.4336
    assert monthly_cost == 2.43


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
                    "minutes": 60,
                }
            }
        ]
    }

    snapshots = allocations_to_snapshots(
        payload,
    )

    assert len(snapshots) == 1

    snapshot = snapshots[0]

    assert (
        snapshot.cpu_request_cores
        == 0.0
    )

    assert (
        snapshot.cpu_usage_cores
        == 0.0
    )

    assert (
        snapshot.memory_request_mib
        == 0.0
    )

    assert (
        snapshot.memory_usage_mib
        == 0.0
    )

    assert (
        snapshot.monthly_cost_usd
        == 0.0
    )


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
                    "minutes": 60,
                    "cpuCoreRequestAverage": 0.5,
                    "cpuCoreUsageAverage": 0.1,
                    "ramByteRequestAverage": 268435456,
                    "ramByteUsageAverage": 67108864,
                    "cpuCost": 0.02,
                    "ramCost": 0.01,
                }
            }
        ]
    }

    snapshots = allocations_to_snapshots(
        payload,
    )

    assert (
        snapshots[0].workload_name
        == "checkoutservice"
    )

    assert (
        snapshots[0].workload_type
        == "Deployment"
    )


def test_pod_is_used_when_controller_is_missing():
    payload = {
        "data": [
            {
                "default/paymentservice": {
                    "properties": {
                        "namespace": "default",
                        "pod": "paymentservice-abc123",
                    },
                    "minutes": 30,
                    "cpuCoreRequestAverage": 0.1,
                    "cpuCoreUsageAverage": 0.001,
                    "ramByteRequestAverage": 67108864,
                    "ramByteUsageAverage": 30000000,
                    "cpuCost": 0.001,
                    "ramCost": 0.0001,
                }
            }
        ]
    }

    snapshots = allocations_to_snapshots(
        payload,
    )

    assert (
        snapshots[0].workload_name
        == "paymentservice-abc123"
    )

    assert (
        snapshots[0].workload_type
        == "Pod"
    )


def test_invalid_data_shape_is_rejected():
    payload = {
        "data": {
            "not": "a list",
        }
    }

    with pytest.raises(
        ValueError,
        match="does not contain a data list",
    ):
        allocations_to_snapshots(
            payload,
        )


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
                    "minutes": 60,
                    "cpuCoreRequestAverage": 1.0,
                    "cpuCoreUsageAverage": 0.4,
                    "ramByteRequestAverage": 536870912,
                    "ramByteUsageAverage": 268435456,
                    "cpuCost": 0.01,
                    "ramCost": 0.01,
                },
                "default/cart": {
                    "properties": {
                        "namespace": "default",
                        "controller": "cartservice",
                        "controllerKind": "Deployment",
                    },
                    "minutes": 60,
                    "cpuCoreRequestAverage": 0.5,
                    "cpuCoreUsageAverage": 0.1,
                    "ramByteRequestAverage": 268435456,
                    "ramByteUsageAverage": 67108864,
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


def test_zero_minute_window_returns_zero_cost():
    allocation = {
        "minutes": 0,
        "cpuCost": 1.0,
        "ramCost": 1.0,
    }

    result = _estimate_monthly_cost(
        allocation,
    )

    assert result == 0.0


def test_invalid_numeric_value_is_rejected():
    payload = {
        "data": [
            {
                "default/frontend": {
                    "properties": {
                        "namespace": "default",
                        "pod": "frontend",
                    },
                    "minutes": 60,
                    "cpuCoreRequestAverage": "invalid",
                }
            }
        ]
    }

    with pytest.raises(
        ValueError,
        match="Unable to convert OpenCost value to float",
    ):
        allocations_to_snapshots(
            payload,
        )

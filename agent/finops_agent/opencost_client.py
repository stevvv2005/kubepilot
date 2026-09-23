from dataclasses import dataclass
from typing import Any, Dict, List
from urllib.parse import urlencode
from urllib.request import urlopen

import json

from agent.finops_agent.cost_analysis import WorkloadCostSnapshot


@dataclass(frozen=True)
class OpenCostClient:
    base_url: str = "http://localhost:9003"

    def _get_json(
        self,
        path: str,
        params: Dict[str, str],
    ) -> Dict[str, Any]:
        query = urlencode(params)

        url = (
            f"{self.base_url.rstrip('/')}"
            f"{path}"
            f"?{query}"
        )

        with urlopen(
            url,
            timeout=10,
        ) as response:
            payload = response.read().decode("utf-8")

        data = json.loads(payload)

        if not isinstance(data, dict):
            raise ValueError(
                "OpenCost response must be a JSON object."
            )

        return data

    def get_allocations(
        self,
        window: str = "1h",
        aggregate: str = "namespace,pod",
    ) -> Dict[str, Any]:
        """
        Fetch OpenCost allocation data.

        Read-only operation.
        """

        return self._get_json(
            path="/allocation/compute",
            params={
                "window": window,
                "aggregate": aggregate,
            },
        )


def _safe_float(
    value: Any,
) -> float:
    if value is None:
        return 0.0

    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Unable to convert OpenCost value to float: {value}"
        ) from exc


def _extract_allocation_entries(
    payload: Dict[str, Any],
) -> List[Dict[str, Any]]:
    data = payload.get("data")

    if not isinstance(data, list):
        raise ValueError(
            "OpenCost allocation response does not contain a data list."
        )

    entries: List[Dict[str, Any]] = []

    for window in data:
        if not isinstance(window, dict):
            continue

        for allocation in window.values():
            if isinstance(allocation, dict):
                entries.append(allocation)

    return entries


def _estimate_monthly_cost(
    allocation: Dict[str, Any],
) -> float:
    """
    Estimate a 30-day monthly cost from the observed
    OpenCost allocation window.

    cpuCost and ramCost represent accumulated cost
    during the allocation's observed duration.
    """

    cpu_cost = _safe_float(
        allocation.get(
            "cpuCost",
            0.0,
        )
    )

    ram_cost = _safe_float(
        allocation.get(
            "ramCost",
            0.0,
        )
    )

    observed_cost = (
        cpu_cost
        + ram_cost
    )

    minutes = _safe_float(
        allocation.get(
            "minutes",
            0.0,
        )
    )

    if minutes <= 0:
        return 0.0

    observed_hours = (
        minutes / 60.0
    )

    hourly_cost = (
        observed_cost
        / observed_hours
    )

    monthly_cost = (
        hourly_cost
        * 24
        * 30
    )

    return round(
        monthly_cost,
        2,
    )


def allocations_to_snapshots(
    payload: Dict[str, Any],
) -> List[WorkloadCostSnapshot]:
    """
    Convert OpenCost allocation data into
    KubePilot WorkloadCostSnapshot objects.

    No write is performed.
    """

    allocations = _extract_allocation_entries(
        payload,
    )

    snapshots: List[WorkloadCostSnapshot] = []

    for allocation in allocations:
        properties = allocation.get(
            "properties",
            {},
        )

        if not isinstance(
            properties,
            dict,
        ):
            properties = {}

        namespace = str(
            properties.get(
                "namespace",
                "unknown",
            )
        )

        workload_name = (
            properties.get(
                "controller"
            )
            or properties.get(
                "pod"
            )
            or allocation.get(
                "name"
            )
            or "unknown"
        )

        workload_type = (
            properties.get(
                "controllerKind"
            )
            or "Pod"
        )

        cpu_request_cores = _safe_float(
            allocation.get(
                "cpuCoreRequestAverage",
                0.0,
            )
        )

        cpu_usage_cores = _safe_float(
            allocation.get(
                "cpuCoreUsageAverage",
                0.0,
            )
        )

        memory_request_bytes = _safe_float(
            allocation.get(
                "ramByteRequestAverage",
                0.0,
            )
        )

        memory_usage_bytes = _safe_float(
            allocation.get(
                "ramByteUsageAverage",
                0.0,
            )
        )

        memory_request_mib = round(
            memory_request_bytes
            / 1024
            / 1024,
            2,
        )

        memory_usage_mib = round(
            memory_usage_bytes
            / 1024
            / 1024,
            2,
        )

        monthly_cost_usd = (
            _estimate_monthly_cost(
                allocation,
            )
        )

        snapshots.append(
            WorkloadCostSnapshot(
                namespace=namespace,
                workload_name=str(
                    workload_name
                ),
                workload_type=str(
                    workload_type
                ),
                cpu_request_cores=(
                    cpu_request_cores
                ),
                cpu_usage_cores=(
                    cpu_usage_cores
                ),
                memory_request_mib=(
                    memory_request_mib
                ),
                memory_usage_mib=(
                    memory_usage_mib
                ),
                monthly_cost_usd=(
                    monthly_cost_usd
                ),
            )
        )

    return snapshots

from dataclasses import dataclass
from typing import Optional

from agent.finops_agent.finops_report import (
    FinOpsReport,
    build_finops_report,
)
from agent.finops_agent.opencost_client import (
    OpenCostClient,
    allocations_to_snapshots,
)


@dataclass(frozen=True)
class LiveFinOpsReport:
    source: str
    namespace_filter: Optional[str]
    report: FinOpsReport
    read_only: bool = True
    performs_write: bool = False


def generate_live_finops_report(
    client: OpenCostClient,
    window: str = "1h",
    namespace: Optional[str] = None,
) -> LiveFinOpsReport:
    """
    Fetch live OpenCost allocations and build
    an aggregated KubePilot FinOps report.

    This operation is strictly read-only.
    """

    payload = client.get_allocations(
        window=window,
    )

    snapshots = allocations_to_snapshots(
        payload,
    )

    if namespace is not None:
        snapshots = [
            snapshot
            for snapshot in snapshots
            if snapshot.namespace == namespace
        ]

    report = build_finops_report(
        snapshots,
    )

    return LiveFinOpsReport(
        source="opencost",
        namespace_filter=namespace,
        report=report,
        read_only=True,
        performs_write=False,
    )

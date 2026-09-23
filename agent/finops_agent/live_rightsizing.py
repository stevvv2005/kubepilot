from dataclasses import dataclass
from typing import Optional, Tuple

from agent.finops_agent.cost_analysis import (
    FinOpsAnalysis,
    analyze_workload_cost,
)
from agent.finops_agent.opencost_client import (
    OpenCostClient,
    allocations_to_snapshots,
)
from agent.finops_agent.rightsizing_proposal import (
    RightsizingProposal,
    build_rightsizing_proposal,
)


@dataclass(frozen=True)
class LiveRightsizingResult:
    source: str
    namespace_filter: Optional[str]
    total_workloads: int
    waste_candidates: int
    proposals: Tuple[RightsizingProposal, ...]
    read_only: bool = True
    performs_write: bool = False
    requires_human_approval: bool = True
    auto_apply: bool = False


def generate_live_rightsizing(
    client: OpenCostClient,
    window: str = "1h",
    namespace: Optional[str] = None,
) -> LiveRightsizingResult:
    """
    Fetch live OpenCost allocations and build
    conservative rightsizing proposals.

    Only workloads classified as underutilized
    receive rightsizing proposals.

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

    proposals = []

    for snapshot in snapshots:
        analysis: FinOpsAnalysis = (
            analyze_workload_cost(
                snapshot,
            )
        )

        if not analysis.waste_detected:
            continue

        proposal = build_rightsizing_proposal(
            snapshot=snapshot,
            analysis=analysis,
        )

        proposals.append(
            proposal,
        )

    return LiveRightsizingResult(
        source="opencost",
        namespace_filter=namespace,
        total_workloads=len(snapshots),
        waste_candidates=len(proposals),
        proposals=tuple(proposals),
        read_only=True,
        performs_write=False,
        requires_human_approval=True,
        auto_apply=False,
    )
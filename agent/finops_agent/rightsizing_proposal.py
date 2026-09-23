from dataclasses import dataclass
from typing import Optional

from agent.finops_agent.cost_analysis import (
    FinOpsAnalysis,
    WorkloadCostSnapshot,
)


@dataclass(frozen=True)
class RightsizingProposal:
    namespace: str
    workload_name: str
    workload_type: str

    current_cpu_request_cores: float
    current_memory_request_mib: float

    suggested_cpu_request_cores: Optional[float]
    suggested_memory_request_mib: Optional[float]

    cpu_utilization_pct: Optional[float]
    memory_utilization_pct: Optional[float]

    current_monthly_cost_usd: float
    estimated_monthly_savings_usd: Optional[float]

    reason: str
    confidence: str

    requires_human_approval: bool = True
    auto_apply: bool = False
    performs_write: bool = False


def _round_cpu_request(
    value: float,
) -> float:
    """
    Round CPU request to a practical Kubernetes value.

    Example:
    0.073 cores -> 0.08 cores
    """

    return round(
        max(value, 0.01),
        2,
    )


def _round_memory_request(
    value: float,
) -> float:
    """
    Round memory request to a practical MiB value.
    """

    rounded = round(
        max(value, 16.0),
    )

    return float(rounded)


def build_rightsizing_proposal(
    snapshot: WorkloadCostSnapshot,
    analysis: FinOpsAnalysis,
) -> RightsizingProposal:
    """
    Build a conservative rightsizing proposal.

    The proposal is created only when the FinOps
    analysis already detected resource waste.

    Suggested requests use observed usage plus a
    conservative safety margin.

    No Kubernetes or Git write is performed.
    """

    if (
        snapshot.namespace
        != analysis.namespace
    ):
        raise ValueError(
            "Snapshot and FinOps analysis namespace do not match."
        )

    if (
        snapshot.workload_name
        != analysis.workload_name
    ):
        raise ValueError(
            "Snapshot and FinOps analysis workload do not match."
        )

    if not analysis.waste_detected:
        return RightsizingProposal(
            namespace=snapshot.namespace,
            workload_name=snapshot.workload_name,
            workload_type=snapshot.workload_type,
            current_cpu_request_cores=(
                snapshot.cpu_request_cores
            ),
            current_memory_request_mib=(
                snapshot.memory_request_mib
            ),
            suggested_cpu_request_cores=None,
            suggested_memory_request_mib=None,
            cpu_utilization_pct=(
                analysis.cpu_utilization_pct
            ),
            memory_utilization_pct=(
                analysis.memory_utilization_pct
            ),
            current_monthly_cost_usd=(
                snapshot.monthly_cost_usd
            ),
            estimated_monthly_savings_usd=(
                analysis.estimated_monthly_savings_usd
            ),
            reason=(
                "No rightsizing proposal generated because "
                "the workload is not classified as underutilized."
            ),
            confidence=analysis.confidence,
            requires_human_approval=True,
            auto_apply=False,
            performs_write=False,
        )

    if (
        snapshot.cpu_usage_cores <= 0
        or snapshot.memory_usage_mib <= 0
    ):
        return RightsizingProposal(
            namespace=snapshot.namespace,
            workload_name=snapshot.workload_name,
            workload_type=snapshot.workload_type,
            current_cpu_request_cores=(
                snapshot.cpu_request_cores
            ),
            current_memory_request_mib=(
                snapshot.memory_request_mib
            ),
            suggested_cpu_request_cores=None,
            suggested_memory_request_mib=None,
            cpu_utilization_pct=(
                analysis.cpu_utilization_pct
            ),
            memory_utilization_pct=(
                analysis.memory_utilization_pct
            ),
            current_monthly_cost_usd=(
                snapshot.monthly_cost_usd
            ),
            estimated_monthly_savings_usd=(
                analysis.estimated_monthly_savings_usd
            ),
            reason=(
                "Observed usage is insufficient for a safe "
                "rightsizing proposal."
            ),
            confidence="low",
            requires_human_approval=True,
            auto_apply=False,
            performs_write=False,
        )

    cpu_with_margin = (
        snapshot.cpu_usage_cores
        * 1.5
    )

    memory_with_margin = (
        snapshot.memory_usage_mib
        * 1.5
    )

    suggested_cpu = min(
        snapshot.cpu_request_cores,
        _round_cpu_request(
            cpu_with_margin,
        ),
    )

    suggested_memory = min(
        snapshot.memory_request_mib,
        _round_memory_request(
            memory_with_margin,
        ),
    )

    return RightsizingProposal(
        namespace=snapshot.namespace,
        workload_name=snapshot.workload_name,
        workload_type=snapshot.workload_type,
        current_cpu_request_cores=(
            snapshot.cpu_request_cores
        ),
        current_memory_request_mib=(
            snapshot.memory_request_mib
        ),
        suggested_cpu_request_cores=(
            suggested_cpu
        ),
        suggested_memory_request_mib=(
            suggested_memory
        ),
        cpu_utilization_pct=(
            analysis.cpu_utilization_pct
        ),
        memory_utilization_pct=(
            analysis.memory_utilization_pct
        ),
        current_monthly_cost_usd=(
            snapshot.monthly_cost_usd
        ),
        estimated_monthly_savings_usd=(
            analysis.estimated_monthly_savings_usd
        ),
        reason=(
            "Workload is underutilized. Suggested requests "
            "are based on observed usage with a 50% safety "
            "margin and require human review before any GitOps change."
        ),
        confidence=analysis.confidence,
        requires_human_approval=True,
        auto_apply=False,
        performs_write=False,
    )
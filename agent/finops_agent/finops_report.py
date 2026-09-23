from dataclasses import dataclass
from typing import Iterable, Tuple

from agent.finops_agent.cost_analysis import (
    FinOpsAnalysis,
    WorkloadCostSnapshot,
    analyze_workload_cost,
)


@dataclass(frozen=True)
class FinOpsReport:
    total_workloads: int
    analyzed_workloads: int
    waste_candidates: int
    total_monthly_cost_usd: float
    estimated_monthly_savings_usd: float
    estimated_savings_pct: float
    recommendations: Tuple[FinOpsAnalysis, ...]
    requires_human_approval: bool = True
    auto_apply: bool = False


def build_finops_report(
    snapshots: Iterable[WorkloadCostSnapshot],
) -> FinOpsReport:
    """
    Build an aggregated FinOps report from workload cost snapshots.

    The report is read-only.

    No Kubernetes mutation, Git write, or automatic
    rightsizing action is performed.
    """

    snapshot_list = list(snapshots)

    analyses = [
        analyze_workload_cost(snapshot)
        for snapshot in snapshot_list
    ]

    recommendations = tuple(
        analysis
        for analysis in analyses
        if analysis.waste_detected
    )

    total_monthly_cost_usd = round(
        sum(
            analysis.monthly_cost_usd
            for analysis in analyses
        ),
        2,
    )

    estimated_monthly_savings_usd = round(
        sum(
            analysis.estimated_monthly_savings_usd or 0.0
            for analysis in recommendations
        ),
        2,
    )

    if total_monthly_cost_usd > 0:
        estimated_savings_pct = round(
            (
                estimated_monthly_savings_usd
                / total_monthly_cost_usd
            )
            * 100,
            2,
        )
    else:
        estimated_savings_pct = 0.0

    return FinOpsReport(
        total_workloads=len(snapshot_list),
        analyzed_workloads=len(analyses),
        waste_candidates=len(recommendations),
        total_monthly_cost_usd=total_monthly_cost_usd,
        estimated_monthly_savings_usd=(
            estimated_monthly_savings_usd
        ),
        estimated_savings_pct=estimated_savings_pct,
        recommendations=recommendations,
        requires_human_approval=True,
        auto_apply=False,
    )

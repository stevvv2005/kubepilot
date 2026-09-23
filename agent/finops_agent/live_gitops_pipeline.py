from dataclasses import dataclass
from typing import Optional, Tuple

from agent.finops_agent.gitops_diff import (
    GitOpsDiffProposal,
    build_gitops_diff_proposal,
)
from agent.finops_agent.live_rightsizing import (
    generate_live_rightsizing,
)
from agent.finops_agent.manifest_inspector import (
    inspect_finops_manifest,
)
from agent.finops_agent.opencost_client import (
    OpenCostClient,
)
from agent.finops_agent.target_file_resolver import (
    resolve_finops_target,
)


@dataclass(frozen=True)
class LiveGitOpsPipelineResult:
    source: str
    namespace_filter: Optional[str]

    total_workloads: int
    waste_candidates: int
    resolved_targets: int
    gitops_diffs: int

    diffs: Tuple[GitOpsDiffProposal, ...]

    read_only: bool = True
    performs_write: bool = False
    writes_file: bool = False
    writes_git: bool = False
    requires_human_approval: bool = True
    auto_apply: bool = False


def generate_live_gitops_pipeline(
    client: OpenCostClient,
    window: str = "1h",
    namespace: Optional[str] = None,
    repository_root: str = ".",
) -> LiveGitOpsPipelineResult:
    """
    Build the complete live FinOps GitOps diff pipeline.

    Flow:

    OpenCost
    -> live rightsizing
    -> GitOps target resolution
    -> manifest inspection
    -> GitOps diff proposal

    This pipeline is strictly read-only.
    """

    rightsizing_result = generate_live_rightsizing(
        client=client,
        window=window,
        namespace=namespace,
    )

    diffs = []
    resolved_targets = 0

    for proposal in rightsizing_result.proposals:
        resolution = resolve_finops_target(
            namespace=proposal.namespace,
            workload_name=proposal.workload_name,
        )

        if not resolution.matched:
            continue

        resolved_targets += 1

        manifest_state = inspect_finops_manifest(
            resolution=resolution,
            repository_root=repository_root,
        )

        if not manifest_state.found:
            continue

        diff = build_gitops_diff_proposal(
            proposal=proposal,
            manifest_state=manifest_state,
        )

        diffs.append(
            diff,
        )

    return LiveGitOpsPipelineResult(
        source=rightsizing_result.source,
        namespace_filter=(
            rightsizing_result.namespace_filter
        ),
        total_workloads=(
            rightsizing_result.total_workloads
        ),
        waste_candidates=(
            rightsizing_result.waste_candidates
        ),
        resolved_targets=resolved_targets,
        gitops_diffs=len(diffs),
        diffs=tuple(diffs),
        read_only=True,
        performs_write=False,
        writes_file=False,
        writes_git=False,
        requires_human_approval=True,
        auto_apply=False,
    )
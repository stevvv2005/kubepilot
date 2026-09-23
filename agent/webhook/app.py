from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agent.finops_agent.approved_manifest import (
    render_approved_finops_manifest,
)
from agent.finops_agent.git_commit_dry_run import (
    build_finops_git_commit_dry_run,
)
from agent.finops_agent.git_execution_gateway import (
    validate_finops_git_execution,
)
from agent.finops_agent.git_execution_request import (
    build_finops_git_execution_request,
)
from agent.finops_agent.git_executor import (
    execute_finops_git_request,
)
from agent.finops_agent.human_approval import (
    FinOpsApprovalDecision,
    apply_finops_approval,
)
from agent.finops_agent.live_gitops_pipeline import (
    generate_live_gitops_pipeline,
)
from agent.finops_agent.live_report import (
    generate_live_finops_report,
)
from agent.finops_agent.live_rightsizing import (
    generate_live_rightsizing,
)
from agent.finops_agent.opencost_client import (
    OpenCostClient,
)

from agent.notifications.slack_payload import (
    build_finops_slack_payload,
    build_sre_slack_payload,
)
from agent.notifications.slack_sender import (
    send_slack_notification,
)

from agent.sre_agent.analyzer import (
    analyze_pod,
)
from agent.sre_agent.approved_manifest import (
    render_approved_manifest,
)
from agent.sre_agent.candidate_value import (
    suggest_candidate_value,
)
from agent.sre_agent.git_change import (
    build_git_change_proposal,
)
from agent.sre_agent.git_commit_dry_run import (
    build_git_commit_dry_run,
)
from agent.sre_agent.git_execution_gateway import (
    validate_git_execution,
)
from agent.sre_agent.git_execution_request import (
    build_git_execution_request,
)
from agent.sre_agent.git_executor import (
    execute_git_request,
)
from agent.sre_agent.github_pr import (
    validate_pr_payload_for_github,
)
from agent.sre_agent.github_request import (
    build_github_pr_request,
)
from agent.sre_agent.human_approval import (
    HumanApprovalDecision,
    apply_human_approval,
)
from agent.sre_agent.manifest_diff import (
    build_manifest_diff_proposal,
)
from agent.sre_agent.patch_proposal import (
    build_patch_proposal,
)
from agent.sre_agent.pr_payload import (
    build_pr_payload,
)
from agent.sre_agent.remediation import (
    build_remediation_proposal,
)
from agent.sre_agent.reviewed_patch import (
    build_reviewed_patch_payload,
)
from agent.sre_agent.target_file_resolver import (
    resolve_target_file,
)


app = FastAPI(
    title="KubePilot SRE Alert Webhook",
    version="1.9.0",
)


class FinOpsApprovalRequest(BaseModel):
    namespace: str
    workload_name: str
    window: str = "1h"

    approved: bool

    approved_cpu_request: Optional[str] = None
    approved_memory_request: Optional[str] = None

    reviewer: str
    reason: str


class Alert(BaseModel):
    status: str
    labels: Dict[str, str] = Field(
        default_factory=dict
    )
    annotations: Dict[str, str] = Field(
        default_factory=dict
    )


class AlertmanagerPayload(BaseModel):
    status: str
    alerts: List[Alert] = Field(
        default_factory=list
    )


class ApprovalRequest(BaseModel):
    namespace: str
    pod_name: str
    container_name: str
    approved: bool
    approved_value: Optional[str] = None
    reviewer: str
    reason: str


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
    }


@app.get("/finops/report")
def get_finops_report(
    namespace: Optional[str] = None,
    window: str = "1h",
) -> dict:
    """
    Return a live read-only FinOps report generated
    from OpenCost.

    This endpoint does not mutate Kubernetes resources,
    Git repositories, or cloud infrastructure.
    """

    client = OpenCostClient()

    try:
        result = generate_live_finops_report(
            client=client,
            window=window,
            namespace=namespace,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Unable to generate FinOps report "
                f"from OpenCost: {exc}"
            ),
        ) from exc

    report = result.report

    return {
        "source": result.source,
        "namespace": result.namespace_filter,
        "read_only": result.read_only,
        "performs_write": result.performs_write,
        "total_workloads": report.total_workloads,
        "analyzed_workloads": (
            report.analyzed_workloads
        ),
        "waste_candidates": (
            report.waste_candidates
        ),
        "total_monthly_cost_usd": (
            report.total_monthly_cost_usd
        ),
        "estimated_monthly_savings_usd": (
            report.estimated_monthly_savings_usd
        ),
        "estimated_savings_pct": (
            report.estimated_savings_pct
        ),
        "requires_human_approval": (
            report.requires_human_approval
        ),
        "auto_apply": report.auto_apply,
        "recommendations": [
            {
                "namespace": (
                    recommendation.namespace
                ),
                "workload_name": (
                    recommendation.workload_name
                ),
                "workload_type": (
                    recommendation.workload_type
                ),
                "cpu_utilization_pct": (
                    recommendation.cpu_utilization_pct
                ),
                "memory_utilization_pct": (
                    recommendation.memory_utilization_pct
                ),
                "monthly_cost_usd": (
                    recommendation.monthly_cost_usd
                ),
                "estimated_monthly_savings_usd": (
                    recommendation
                    .estimated_monthly_savings_usd
                ),
                "confidence": (
                    recommendation.confidence
                ),
                "recommendation": (
                    recommendation.recommendation
                ),
                "requires_human_approval": (
                    recommendation
                    .requires_human_approval
                ),
                "auto_apply": (
                    recommendation.auto_apply
                ),
            }
            for recommendation
            in report.recommendations
        ],
    }


@app.get("/finops/rightsizing")
def get_finops_rightsizing(
    namespace: Optional[str] = None,
    window: str = "1h",
) -> dict:
    """
    Return live read-only FinOps rightsizing proposals
    generated from OpenCost allocation data.
    """

    client = OpenCostClient()

    try:
        result = generate_live_rightsizing(
            client=client,
            window=window,
            namespace=namespace,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Unable to generate FinOps rightsizing "
                f"proposals from OpenCost: {exc}"
            ),
        ) from exc

    return {
        "source": result.source,
        "namespace": result.namespace_filter,
        "total_workloads": (
            result.total_workloads
        ),
        "waste_candidates": (
            result.waste_candidates
        ),
        "read_only": result.read_only,
        "performs_write": (
            result.performs_write
        ),
        "requires_human_approval": (
            result.requires_human_approval
        ),
        "auto_apply": result.auto_apply,
        "proposals": [
            {
                "namespace": proposal.namespace,
                "workload_name": (
                    proposal.workload_name
                ),
                "workload_type": (
                    proposal.workload_type
                ),
                "current_cpu_request_cores": (
                    proposal
                    .current_cpu_request_cores
                ),
                "current_memory_request_mib": (
                    proposal
                    .current_memory_request_mib
                ),
                "suggested_cpu_request_cores": (
                    proposal
                    .suggested_cpu_request_cores
                ),
                "suggested_memory_request_mib": (
                    proposal
                    .suggested_memory_request_mib
                ),
                "cpu_utilization_pct": (
                    proposal.cpu_utilization_pct
                ),
                "memory_utilization_pct": (
                    proposal
                    .memory_utilization_pct
                ),
                "current_monthly_cost_usd": (
                    proposal
                    .current_monthly_cost_usd
                ),
                "estimated_monthly_savings_usd": (
                    proposal
                    .estimated_monthly_savings_usd
                ),
                "reason": proposal.reason,
                "confidence": proposal.confidence,
                "requires_human_approval": (
                    proposal
                    .requires_human_approval
                ),
                "auto_apply": (
                    proposal.auto_apply
                ),
                "performs_write": (
                    proposal.performs_write
                ),
            }
            for proposal in result.proposals
        ],
    }


@app.post("/finops/approvals")
def approve_finops_change(
    request: FinOpsApprovalRequest,
) -> dict:
    """
    Review a live FinOps GitOps diff and build
    the complete approved Git dry-run pipeline.

    Slack notification remains dry-run only.

    Real Git execution and real Slack delivery
    remain disabled.
    """

    client = OpenCostClient()

    try:
        pipeline = generate_live_gitops_pipeline(
            client=client,
            window=request.window,
            namespace=request.namespace,
            repository_root=".",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Unable to generate live FinOps "
                "GitOps pipeline: "
                f"{type(exc).__name__}: {exc}"
            ),
        ) from exc

    matching_diff = next(
        (
            diff
            for diff in pipeline.diffs
            if (
                diff.workload_name
                == request.workload_name
                or diff.manifest_name
                == request.workload_name
            )
        ),
        None,
    )

    if matching_diff is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No live FinOps GitOps diff "
                "was found for the requested workload."
            ),
        )

    decision = FinOpsApprovalDecision(
        approved=request.approved,
        approved_cpu_request=(
            request.approved_cpu_request
        ),
        approved_memory_request=(
            request.approved_memory_request
        ),
        reviewer=request.reviewer,
        reason=request.reason,
    )

    try:
        approved_change = apply_finops_approval(
            diff=matching_diff,
            decision=decision,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    approved_manifest = None
    commit_plan = None
    execution_gateway = None
    execution_request = None
    execution_result = None

    if approved_change.ready_for_render:
        try:
            approved_manifest = (
                render_approved_finops_manifest(
                    approved_change=(
                        approved_change
                    ),
                    repository_root=".",
                )
            )

            commit_plan = (
                build_finops_git_commit_dry_run(
                    approved_manifest
                )
            )

            execution_gateway = (
                validate_finops_git_execution(
                    commit_plan
                )
            )

            if (
                execution_gateway.allowed
                and execution_gateway
                .ready_to_execute
            ):
                execution_request = (
                    build_finops_git_execution_request(
                        commit_plan=commit_plan,
                        gateway=execution_gateway,
                        repository=(
                            "stevvv2005/kubepilot"
                        ),
                        base_branch="main",
                    )
                )

                execution_result = (
                    execute_finops_git_request(
                        request=execution_request,
                        dry_run=True,
                    )
                )

        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

    estimated_monthly_savings_usd = float(
        matching_diff
        .estimated_monthly_savings_usd
        or 0.0
    )

    # Temporary approximation:
    # current FinOps waste rule estimates
    # savings as 25% of current monthly cost.
    #
    # This will later be replaced with the
    # original OpenCost monthly cost value.
    current_monthly_cost_usd = (
        estimated_monthly_savings_usd
        * 4.0
    )

    slack_payload = build_finops_slack_payload(
        namespace=request.namespace,
        workload_name=(
            matching_diff.manifest_name
        ),
        current_monthly_cost_usd=(
            current_monthly_cost_usd
        ),
        estimated_monthly_savings_usd=(
            estimated_monthly_savings_usd
        ),
        current_cpu_request=(
            matching_diff.current_cpu_request
        ),
        proposed_cpu_request=(
            approved_change
            .approved_cpu_request
            if approved_change.approved
            else matching_diff
            .proposed_cpu_request
        ),
        current_memory_request=(
            matching_diff
            .current_memory_request
        ),
        proposed_memory_request=(
            approved_change
            .approved_memory_request
            if approved_change.approved
            else matching_diff
            .proposed_memory_request
        ),
        confidence=matching_diff.confidence,
        requires_human_approval=(
            matching_diff
            .requires_human_approval
        ),
        dry_run=True,
    )

    slack_result = send_slack_notification(
        payload=slack_payload,
        destination="#kubepilot-finops",
        dry_run=True,
    )

    return {
        "pipeline": {
            "source": pipeline.source,
            "namespace": (
                pipeline.namespace_filter
            ),
            "total_workloads": (
                pipeline.total_workloads
            ),
            "waste_candidates": (
                pipeline.waste_candidates
            ),
            "resolved_targets": (
                pipeline.resolved_targets
            ),
            "gitops_diffs": (
                pipeline.gitops_diffs
            ),
            "read_only": pipeline.read_only,
            "performs_write": (
                pipeline.performs_write
            ),
        },

        "gitops_diff": {
            "workload_name": (
                matching_diff.workload_name
            ),
            "target_file": (
                matching_diff.target_file
            ),
            "manifest_kind": (
                matching_diff.manifest_kind
            ),
            "manifest_name": (
                matching_diff.manifest_name
            ),
            "container_name": (
                matching_diff.container_name
            ),
            "current_cpu_request": (
                matching_diff
                .current_cpu_request
            ),
            "proposed_cpu_request": (
                matching_diff
                .proposed_cpu_request
            ),
            "current_memory_request": (
                matching_diff
                .current_memory_request
            ),
            "proposed_memory_request": (
                matching_diff
                .proposed_memory_request
            ),
            "estimated_monthly_savings_usd": (
                matching_diff
                .estimated_monthly_savings_usd
            ),
            "requires_human_approval": (
                matching_diff
                .requires_human_approval
            ),
            "writes_file": (
                matching_diff.writes_file
            ),
            "writes_git": (
                matching_diff.writes_git
            ),
            "auto_apply": (
                matching_diff.auto_apply
            ),
        },

        "approval": {
            "approved": (
                approved_change.approved
            ),
            "reviewer": (
                approved_change.reviewer
            ),
            "reason": (
                approved_change.reason
            ),
            "approved_cpu_request": (
                approved_change
                .approved_cpu_request
            ),
            "approved_memory_request": (
                approved_change
                .approved_memory_request
            ),
            "ready_for_render": (
                approved_change
                .ready_for_render
            ),
            "writes_file": (
                approved_change.writes_file
            ),
            "writes_git": (
                approved_change.writes_git
            ),
            "auto_apply": (
                approved_change.auto_apply
            ),
        },

        "approved_manifest": (
            {
                "target_file": (
                    approved_manifest.target_file
                ),
                "manifest_kind": (
                    approved_manifest
                    .manifest_kind
                ),
                "manifest_name": (
                    approved_manifest
                    .manifest_name
                ),
                "container_name": (
                    approved_manifest
                    .container_name
                ),
                "approved_cpu_request": (
                    approved_manifest
                    .approved_cpu_request
                ),
                "approved_memory_request": (
                    approved_manifest
                    .approved_memory_request
                ),
                "rendered_yaml": (
                    approved_manifest
                    .rendered_yaml
                ),
                "ready_for_commit": (
                    approved_manifest
                    .ready_for_commit
                ),
                "writes_file": (
                    approved_manifest
                    .writes_file
                ),
                "writes_git": (
                    approved_manifest
                    .writes_git
                ),
            }
            if approved_manifest is not None
            else None
        ),

        "git_commit_dry_run": (
            {
                "target_file": (
                    commit_plan.target_file
                ),
                "branch_name": (
                    commit_plan.branch_name
                ),
                "commit_message": (
                    commit_plan.commit_message
                ),
                "rendered_yaml": (
                    commit_plan.rendered_yaml
                ),
                "ready_to_commit": (
                    commit_plan.ready_to_commit
                ),
                "performs_write": (
                    commit_plan.performs_write
                ),
                "writes_file": (
                    commit_plan.writes_file
                ),
                "writes_git": (
                    commit_plan.writes_git
                ),
            }
            if commit_plan is not None
            else None
        ),

        "git_execution_gateway": (
            {
                "allowed": (
                    execution_gateway.allowed
                ),
                "reason": (
                    execution_gateway.reason
                ),
                "ready_to_execute": (
                    execution_gateway
                    .ready_to_execute
                ),
                "performs_write": (
                    execution_gateway
                    .performs_write
                ),
            }
            if execution_gateway is not None
            else None
        ),

        "git_execution_request": (
            {
                "repository": (
                    execution_request.repository
                ),
                "base_branch": (
                    execution_request.base_branch
                ),
                "head_branch": (
                    execution_request.head_branch
                ),
                "target_file": (
                    execution_request.target_file
                ),
                "commit_message": (
                    execution_request
                    .commit_message
                ),
                "pr_title": (
                    execution_request.pr_title
                ),
                "pr_body": (
                    execution_request.pr_body
                ),
                "create_branch": (
                    execution_request
                    .create_branch
                ),
                "write_file": (
                    execution_request.write_file
                ),
                "create_commit": (
                    execution_request
                    .create_commit
                ),
                "push_branch": (
                    execution_request
                    .push_branch
                ),
                "create_pr": (
                    execution_request.create_pr
                ),
                "authorized": (
                    execution_request.authorized
                ),
                "performs_write": (
                    execution_request
                    .performs_write
                ),
            }
            if execution_request is not None
            else None
        ),

        "git_execution_result": (
            {
                "repository": (
                    execution_result.repository
                ),
                "base_branch": (
                    execution_result.base_branch
                ),
                "head_branch": (
                    execution_result.head_branch
                ),
                "target_file": (
                    execution_result.target_file
                ),
                "commit_message": (
                    execution_result
                    .commit_message
                ),
                "dry_run": (
                    execution_result.dry_run
                ),
                "would_create_branch": (
                    execution_result
                    .would_create_branch
                ),
                "would_write_file": (
                    execution_result
                    .would_write_file
                ),
                "would_create_commit": (
                    execution_result
                    .would_create_commit
                ),
                "would_push_branch": (
                    execution_result
                    .would_push_branch
                ),
                "would_create_pr": (
                    execution_result
                    .would_create_pr
                ),
                "executed": (
                    execution_result.executed
                ),
                "performs_write": (
                    execution_result
                    .performs_write
                ),
            }
            if execution_result is not None
            else None
        ),

        "slack_notification": {
            "notification_type": (
                slack_result.notification_type
            ),
            "title": slack_result.title,
            "destination": (
                slack_result.destination
            ),
            "dry_run": slack_result.dry_run,
            "would_send": (
                slack_result.would_send
            ),
            "sent": slack_result.sent,
            "performs_write": (
                slack_result.performs_write
            ),
        },
    }


@app.post("/alerts")
def receive_alerts(
    payload: AlertmanagerPayload,
) -> dict:
    """
    Receive Alertmanager alerts and generate
    the SRE remediation pipeline.

    Slack remains dry-run only.
    """

    if not payload.alerts:
        raise HTTPException(
            status_code=400,
            detail=(
                "Alertmanager payload "
                "contains no alerts"
            ),
        )

    first_alert = payload.alerts[0]

    namespace = first_alert.labels.get(
        "namespace"
    )
    pod = first_alert.labels.get(
        "pod"
    )
    container = first_alert.labels.get(
        "container"
    )

    if (
        not namespace
        or not pod
        or not container
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Alert must contain namespace, "
                "pod, and container labels"
            ),
        )

    target_resolution = resolve_target_file(
        namespace=namespace,
        pod_name=pod,
        container_name=container,
    )

    analysis = analyze_pod(
        namespace=namespace,
        pod_name=pod,
        container_name=container,
    )

    remediation = build_remediation_proposal(
        analysis.diagnosis,
        target_file=(
            target_resolution.target_file
        ),
    )

    git_change = build_git_change_proposal(
        remediation,
    )

    manifest_diff = (
        build_manifest_diff_proposal(
            git_change=git_change,
            container_name=container,
        )
    )

    patch_proposal = build_patch_proposal(
        manifest_diff=manifest_diff,
        container_name=container,
    )

    candidate_value = (
        suggest_candidate_value(
            incident_type=(
                patch_proposal.incident_type
            ),
            field=patch_proposal.field,
            current_value=(
                patch_proposal.current_value
            ),
        )
    )

    reviewed_patch = (
        build_reviewed_patch_payload(
            patch_proposal=patch_proposal,
            candidate_value=candidate_value,
        )
    )

    pr_payload = build_pr_payload(
        reviewed_patch=reviewed_patch,
    )

    github_pr_gateway = (
        validate_pr_payload_for_github(
            payload=pr_payload,
        )
    )

    github_pr_request = (
        build_github_pr_request(
            repository=(
                "stevvv2005/kubepilot"
            ),
            base_branch="main",
            payload=pr_payload,
            gateway=github_pr_gateway,
        )
    )

    slack_payload = build_sre_slack_payload(
        incident_type=(
            analysis.diagnosis.incident_type
        ),
        namespace=namespace,
        workload_name=pod,
        root_cause=(
            analysis.diagnosis.root_cause
        ),
        recommendation=(
            analysis.diagnosis.recommendation
        ),
        confidence=(
            analysis.diagnosis.confidence
        ),
        requires_human_approval=(
            remediation
            .requires_human_approval
        ),
        dry_run=True,
    )

    slack_result = send_slack_notification(
        payload=slack_payload,
        destination="#kubepilot-alerts",
        dry_run=True,
    )

    return {
        "received": len(payload.alerts),
        "status": first_alert.status,
        "alertname": (
            first_alert.labels.get(
                "alertname"
            )
        ),
        "namespace": namespace,
        "pod": pod,
        "container": container,
        "severity": (
            first_alert.labels.get(
                "severity"
            )
        ),

        "target_file_resolution": {
            "namespace": (
                target_resolution.namespace
            ),
            "pod_name": (
                target_resolution.pod_name
            ),
            "container_name": (
                target_resolution.container_name
            ),
            "target_file": (
                target_resolution.target_file
            ),
            "matched": (
                target_resolution.matched
            ),
            "reason": (
                target_resolution.reason
            ),
        },

        "diagnosis": {
            "incident_type": (
                analysis.diagnosis
                .incident_type
            ),
            "root_cause": (
                analysis.diagnosis
                .root_cause
            ),
            "recommendation": (
                analysis.diagnosis
                .recommendation
            ),
            "confidence": (
                analysis.diagnosis
                .confidence
            ),
        },

        "metrics": {
            "memory_mib": (
                analysis.memory_mib
            ),
            "cpu_millicores": (
                analysis.cpu_millicores
            ),
        },

        "remediation": {
            "incident_type": (
                remediation.incident_type
            ),
            "summary": (
                remediation.summary
            ),
            "proposed_change": (
                remediation.proposed_change
            ),
            "target_file": (
                remediation.target_file
            ),
            "requires_human_approval": (
                remediation
                .requires_human_approval
            ),
            "direct_cluster_write": (
                remediation
                .direct_cluster_write
            ),
        },

        "git_change": {
            "incident_type": (
                git_change.incident_type
            ),
            "target_file": (
                git_change.target_file
            ),
            "change_type": (
                git_change.change_type
            ),
            "description": (
                git_change.description
            ),
            "requires_human_approval": (
                git_change
                .requires_human_approval
            ),
            "apply_directly": (
                git_change.apply_directly
            ),
        },

        "manifest_diff": {
            "incident_type": (
                manifest_diff.incident_type
            ),
            "target_file": (
                manifest_diff.target_file
            ),
            "change_type": (
                manifest_diff.change_type
            ),
            "before": (
                manifest_diff.before
            ),
            "after": (
                manifest_diff.after
            ),
            "requires_human_approval": (
                manifest_diff
                .requires_human_approval
            ),
            "writes_file": (
                manifest_diff.writes_file
            ),
        },

        "patch_proposal": {
            "incident_type": (
                patch_proposal.incident_type
            ),
            "target_file": (
                patch_proposal.target_file
            ),
            "container_name": (
                patch_proposal.container_name
            ),
            "field": (
                patch_proposal.field
            ),
            "current_value": (
                patch_proposal.current_value
            ),
            "proposed_value": (
                patch_proposal.proposed_value
            ),
            "reason": (
                patch_proposal.reason
            ),
            "requires_human_approval": (
                patch_proposal
                .requires_human_approval
            ),
            "writes_file": (
                patch_proposal.writes_file
            ),
        },

        "candidate_value": {
            "incident_type": (
                candidate_value.incident_type
            ),
            "field": (
                candidate_value.field
            ),
            "current_value": (
                candidate_value.current_value
            ),
            "candidate_value": (
                candidate_value.candidate_value
            ),
            "reason": (
                candidate_value.reason
            ),
            "confidence": (
                candidate_value.confidence
            ),
            "requires_human_approval": (
                candidate_value
                .requires_human_approval
            ),
            "auto_apply": (
                candidate_value.auto_apply
            ),
        },

        "reviewed_patch": {
            "incident_type": (
                reviewed_patch.incident_type
            ),
            "target_file": (
                reviewed_patch.target_file
            ),
            "container_name": (
                reviewed_patch.container_name
            ),
            "field": reviewed_patch.field,
            "current_value": (
                reviewed_patch.current_value
            ),
            "candidate_value": (
                reviewed_patch.candidate_value
            ),
            "approved_value": (
                reviewed_patch.approved_value
            ),
            "reason": reviewed_patch.reason,
            "confidence": (
                reviewed_patch.confidence
            ),
            "requires_human_approval": (
                reviewed_patch
                .requires_human_approval
            ),
            "ready_for_pr": (
                reviewed_patch.ready_for_pr
            ),
            "writes_file": (
                reviewed_patch.writes_file
            ),
            "auto_apply": (
                reviewed_patch.auto_apply
            ),
        },

        "pr_payload": {
            "incident_type": (
                pr_payload.incident_type
            ),
            "title": pr_payload.title,
            "branch_name": (
                pr_payload.branch_name
            ),
            "target_file": (
                pr_payload.target_file
            ),
            "container_name": (
                pr_payload.container_name
            ),
            "field": pr_payload.field,
            "current_value": (
                pr_payload.current_value
            ),
            "approved_value": (
                pr_payload.approved_value
            ),
            "commit_message": (
                pr_payload.commit_message
            ),
            "pr_body": (
                pr_payload.pr_body
            ),
            "ready_to_create": (
                pr_payload.ready_to_create
            ),
            "writes_git": (
                pr_payload.writes_git
            ),
            "creates_pr": (
                pr_payload.creates_pr
            ),
        },

        "github_pr_gateway": {
            "allowed": (
                github_pr_gateway.allowed
            ),
            "reason": (
                github_pr_gateway.reason
            ),
            "ready_to_send": (
                github_pr_gateway
                .ready_to_send
            ),
            "performs_write": (
                github_pr_gateway
                .performs_write
            ),
        },

        "github_pr_request": {
            "repository": (
                github_pr_request.repository
            ),
            "base_branch": (
                github_pr_request.base_branch
            ),
            "head_branch": (
                github_pr_request.head_branch
            ),
            "title": (
                github_pr_request.title
            ),
            "body": (
                github_pr_request.body
            ),
            "target_file": (
                github_pr_request.target_file
            ),
            "approved_value": (
                github_pr_request.approved_value
            ),
            "ready_to_send": (
                github_pr_request
                .ready_to_send
            ),
            "performs_write": (
                github_pr_request
                .performs_write
            ),
        },

        "slack_notification": {
            "notification_type": (
                slack_result.notification_type
            ),
            "title": slack_result.title,
            "destination": (
                slack_result.destination
            ),
            "dry_run": (
                slack_result.dry_run
            ),
            "would_send": (
                slack_result.would_send
            ),
            "sent": slack_result.sent,
            "performs_write": (
                slack_result.performs_write
            ),
        },
    }


@app.post("/approvals")
def approve_remediation(
    request: ApprovalRequest,
) -> dict:
    """
    Apply a human SRE approval decision and
    build the safe Git dry-run flow.
    """

    target_resolution = resolve_target_file(
        namespace=request.namespace,
        pod_name=request.pod_name,
        container_name=(
            request.container_name
        ),
    )

    if not target_resolution.matched:
        raise HTTPException(
            status_code=400,
            detail=(
                "No allowlisted GitOps target "
                "file matches this workload."
            ),
        )

    analysis = analyze_pod(
        namespace=request.namespace,
        pod_name=request.pod_name,
        container_name=(
            request.container_name
        ),
    )

    remediation = (
        build_remediation_proposal(
            analysis.diagnosis,
            target_file=(
                target_resolution.target_file
            ),
        )
    )

    git_change = build_git_change_proposal(
        remediation,
    )

    manifest_diff = (
        build_manifest_diff_proposal(
            git_change=git_change,
            container_name=(
                request.container_name
            ),
        )
    )

    patch_proposal = (
        build_patch_proposal(
            manifest_diff=manifest_diff,
            container_name=(
                request.container_name
            ),
        )
    )

    candidate_value = (
        suggest_candidate_value(
            incident_type=(
                patch_proposal.incident_type
            ),
            field=patch_proposal.field,
            current_value=(
                patch_proposal.current_value
            ),
        )
    )

    decision = HumanApprovalDecision(
        approved=request.approved,
        approved_value=(
            request.approved_value
        ),
        reviewer=request.reviewer,
        reason=request.reason,
    )

    try:
        reviewed_patch = apply_human_approval(
            patch_proposal=patch_proposal,
            candidate_value=(
                candidate_value
            ),
            decision=decision,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    approved_manifest = None

    if reviewed_patch.ready_for_pr:
        try:
            approved_manifest = (
                render_approved_manifest(
                    reviewed_patch=(
                        reviewed_patch
                    ),
                    repository_root=".",
                )
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

    pr_payload = build_pr_payload(
        reviewed_patch=reviewed_patch,
    )

    git_commit_dry_run = None

    if approved_manifest is not None:
        try:
            git_commit_dry_run = (
                build_git_commit_dry_run(
                    approved_manifest=(
                        approved_manifest
                    ),
                    pr_payload=pr_payload,
                )
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

    github_pr_gateway = (
        validate_pr_payload_for_github(
            payload=pr_payload,
        )
    )

    git_execution_gateway = None

    if git_commit_dry_run is not None:
        git_execution_gateway = (
            validate_git_execution(
                commit_plan=(
                    git_commit_dry_run
                ),
                pr_payload=pr_payload,
                github_gateway=(
                    github_pr_gateway
                ),
            )
        )

    github_pr_request = (
        build_github_pr_request(
            repository=(
                "stevvv2005/kubepilot"
            ),
            base_branch="main",
            payload=pr_payload,
            gateway=github_pr_gateway,
        )
    )

    git_execution_request = None

    if (
        git_commit_dry_run is not None
        and git_execution_gateway
        is not None
        and git_execution_gateway.allowed
        and git_execution_gateway
        .ready_to_execute
    ):
        try:
            git_execution_request = (
                build_git_execution_request(
                    commit_plan=(
                        git_commit_dry_run
                    ),
                    execution_gateway=(
                        git_execution_gateway
                    ),
                    github_request=(
                        github_pr_request
                    ),
                )
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

    git_execution_result = None

    if git_execution_request is not None:
        try:
            git_execution_result = (
                execute_git_request(
                    request=(
                        git_execution_request
                    ),
                    dry_run=True,
                )
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

    return {
        "approval": {
            "approved": request.approved,
            "approved_value": (
                reviewed_patch.approved_value
            ),
            "reviewer": request.reviewer,
            "reason": request.reason,
        },

        "target_file_resolution": {
            "target_file": (
                target_resolution.target_file
            ),
            "matched": (
                target_resolution.matched
            ),
            "reason": (
                target_resolution.reason
            ),
        },

        "candidate_value": {
            "candidate_value": (
                candidate_value.candidate_value
            ),
            "confidence": (
                candidate_value.confidence
            ),
            "auto_apply": (
                candidate_value.auto_apply
            ),
        },

        "reviewed_patch": {
            "incident_type": (
                reviewed_patch.incident_type
            ),
            "target_file": (
                reviewed_patch.target_file
            ),
            "container_name": (
                reviewed_patch.container_name
            ),
            "field": reviewed_patch.field,
            "current_value": (
                reviewed_patch.current_value
            ),
            "candidate_value": (
                reviewed_patch.candidate_value
            ),
            "approved_value": (
                reviewed_patch.approved_value
            ),
            "ready_for_pr": (
                reviewed_patch.ready_for_pr
            ),
            "writes_file": (
                reviewed_patch.writes_file
            ),
            "auto_apply": (
                reviewed_patch.auto_apply
            ),
        },

        "approved_manifest": (
            {
                "target_file": (
                    approved_manifest.target_file
                ),
                "container_name": (
                    approved_manifest
                    .container_name
                ),
                "field": (
                    approved_manifest.field
                ),
                "approved_value": (
                    approved_manifest
                    .approved_value
                ),
                "rendered_yaml": (
                    approved_manifest
                    .rendered_yaml
                ),
                "ready_for_commit": (
                    approved_manifest
                    .ready_for_commit
                ),
                "writes_file": (
                    approved_manifest
                    .writes_file
                ),
                "writes_git": (
                    approved_manifest
                    .writes_git
                ),
            }
            if approved_manifest is not None
            else None
        ),

        "pr_payload": {
            "title": pr_payload.title,
            "branch_name": (
                pr_payload.branch_name
            ),
            "target_file": (
                pr_payload.target_file
            ),
            "approved_value": (
                pr_payload.approved_value
            ),
            "commit_message": (
                pr_payload.commit_message
            ),
            "ready_to_create": (
                pr_payload.ready_to_create
            ),
            "writes_git": (
                pr_payload.writes_git
            ),
            "creates_pr": (
                pr_payload.creates_pr
            ),
        },

        "git_commit_dry_run": (
            {
                "target_file": (
                    git_commit_dry_run
                    .target_file
                ),
                "branch_name": (
                    git_commit_dry_run
                    .branch_name
                ),
                "commit_message": (
                    git_commit_dry_run
                    .commit_message
                ),
                "rendered_yaml": (
                    git_commit_dry_run
                    .rendered_yaml
                ),
                "ready_to_commit": (
                    git_commit_dry_run
                    .ready_to_commit
                ),
                "performs_write": (
                    git_commit_dry_run
                    .performs_write
                ),
                "writes_file": (
                    git_commit_dry_run
                    .writes_file
                ),
                "writes_git": (
                    git_commit_dry_run
                    .writes_git
                ),
            }
            if git_commit_dry_run is not None
            else None
        ),

        "git_execution_gateway": (
            {
                "allowed": (
                    git_execution_gateway
                    .allowed
                ),
                "reason": (
                    git_execution_gateway
                    .reason
                ),
                "ready_to_execute": (
                    git_execution_gateway
                    .ready_to_execute
                ),
                "performs_write": (
                    git_execution_gateway
                    .performs_write
                ),
            }
            if git_execution_gateway is not None
            else None
        ),

        "git_execution_request": (
            {
                "repository": (
                    git_execution_request
                    .repository
                ),
                "base_branch": (
                    git_execution_request
                    .base_branch
                ),
                "head_branch": (
                    git_execution_request
                    .head_branch
                ),
                "target_file": (
                    git_execution_request
                    .target_file
                ),
                "commit_message": (
                    git_execution_request
                    .commit_message
                ),
                "rendered_yaml": (
                    git_execution_request
                    .rendered_yaml
                ),
                "pr_title": (
                    git_execution_request
                    .pr_title
                ),
                "pr_body": (
                    git_execution_request
                    .pr_body
                ),
                "create_branch": (
                    git_execution_request
                    .create_branch
                ),
                "write_file": (
                    git_execution_request
                    .write_file
                ),
                "create_commit": (
                    git_execution_request
                    .create_commit
                ),
                "push_branch": (
                    git_execution_request
                    .push_branch
                ),
                "create_pr": (
                    git_execution_request
                    .create_pr
                ),
                "authorized": (
                    git_execution_request
                    .authorized
                ),
                "performs_write": (
                    git_execution_request
                    .performs_write
                ),
            }
            if git_execution_request
            is not None
            else None
        ),

        "git_execution_result": (
            {
                "repository": (
                    git_execution_result
                    .repository
                ),
                "base_branch": (
                    git_execution_result
                    .base_branch
                ),
                "head_branch": (
                    git_execution_result
                    .head_branch
                ),
                "target_file": (
                    git_execution_result
                    .target_file
                ),
                "commit_message": (
                    git_execution_result
                    .commit_message
                ),
                "dry_run": (
                    git_execution_result
                    .dry_run
                ),
                "would_create_branch": (
                    git_execution_result
                    .would_create_branch
                ),
                "would_write_file": (
                    git_execution_result
                    .would_write_file
                ),
                "would_create_commit": (
                    git_execution_result
                    .would_create_commit
                ),
                "would_push_branch": (
                    git_execution_result
                    .would_push_branch
                ),
                "would_create_pr": (
                    git_execution_result
                    .would_create_pr
                ),
                "executed": (
                    git_execution_result
                    .executed
                ),
                "performs_write": (
                    git_execution_result
                    .performs_write
                ),
            }
            if git_execution_result
            is not None
            else None
        ),

        "github_pr_gateway": {
            "allowed": (
                github_pr_gateway.allowed
            ),
            "reason": (
                github_pr_gateway.reason
            ),
            "ready_to_send": (
                github_pr_gateway
                .ready_to_send
            ),
            "performs_write": (
                github_pr_gateway
                .performs_write
            ),
        },

        "github_pr_request": {
            "repository": (
                github_pr_request.repository
            ),
            "base_branch": (
                github_pr_request.base_branch
            ),
            "head_branch": (
                github_pr_request.head_branch
            ),
            "title": (
                github_pr_request.title
            ),
            "target_file": (
                github_pr_request.target_file
            ),
            "approved_value": (
                github_pr_request
                .approved_value
            ),
            "ready_to_send": (
                github_pr_request
                .ready_to_send
            ),
            "performs_write": (
                github_pr_request
                .performs_write
            ),
        },
    }
from typing import Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agent.sre_agent.analyzer import analyze_pod
from agent.sre_agent.candidate_value import suggest_candidate_value
from agent.sre_agent.git_change import build_git_change_proposal
from agent.sre_agent.manifest_diff import build_manifest_diff_proposal
from agent.sre_agent.patch_proposal import build_patch_proposal
from agent.sre_agent.remediation import build_remediation_proposal
from agent.sre_agent.reviewed_patch import build_reviewed_patch_payload


app = FastAPI(
    title="KubePilot SRE Alert Webhook",
    version="0.8.0",
)


class Alert(BaseModel):
    status: str
    labels: Dict[str, str] = Field(default_factory=dict)
    annotations: Dict[str, str] = Field(default_factory=dict)


class AlertmanagerPayload(BaseModel):
    status: str
    alerts: List[Alert] = Field(default_factory=list)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/alerts")
def receive_alerts(payload: AlertmanagerPayload) -> dict:
    if not payload.alerts:
        raise HTTPException(
            status_code=400,
            detail="Alertmanager payload contains no alerts",
        )

    first_alert = payload.alerts[0]

    namespace = first_alert.labels.get("namespace")
    pod = first_alert.labels.get("pod")
    container = first_alert.labels.get("container")

    if not namespace or not pod or not container:
        raise HTTPException(
            status_code=400,
            detail="Alert must contain namespace, pod, and container labels",
        )

    analysis = analyze_pod(
        namespace=namespace,
        pod_name=pod,
        container_name=container,
    )

    remediation = build_remediation_proposal(
        analysis.diagnosis,
    )

    git_change = build_git_change_proposal(
        remediation,
    )

    manifest_diff = build_manifest_diff_proposal(
        git_change=git_change,
        container_name=container,
    )

    patch_proposal = build_patch_proposal(
        manifest_diff=manifest_diff,
        container_name=container,
    )

    candidate_value = suggest_candidate_value(
        incident_type=patch_proposal.incident_type,
        field=patch_proposal.field,
        current_value=patch_proposal.current_value,
    )

    reviewed_patch = build_reviewed_patch_payload(
        patch_proposal=patch_proposal,
        candidate_value=candidate_value,
    )

    return {
        "received": len(payload.alerts),
        "status": first_alert.status,
        "alertname": first_alert.labels.get("alertname"),
        "namespace": namespace,
        "pod": pod,
        "container": container,
        "severity": first_alert.labels.get("severity"),
        "diagnosis": {
            "incident_type": analysis.diagnosis.incident_type,
            "root_cause": analysis.diagnosis.root_cause,
            "recommendation": analysis.diagnosis.recommendation,
            "confidence": analysis.diagnosis.confidence,
        },
        "metrics": {
            "memory_mib": analysis.memory_mib,
            "cpu_millicores": analysis.cpu_millicores,
        },
        "remediation": {
            "incident_type": remediation.incident_type,
            "summary": remediation.summary,
            "proposed_change": remediation.proposed_change,
            "target_file": remediation.target_file,
            "requires_human_approval": (
                remediation.requires_human_approval
            ),
            "direct_cluster_write": remediation.direct_cluster_write,
        },
        "git_change": {
            "incident_type": git_change.incident_type,
            "target_file": git_change.target_file,
            "change_type": git_change.change_type,
            "description": git_change.description,
            "requires_human_approval": (
                git_change.requires_human_approval
            ),
            "apply_directly": git_change.apply_directly,
        },
        "manifest_diff": {
            "incident_type": manifest_diff.incident_type,
            "target_file": manifest_diff.target_file,
            "change_type": manifest_diff.change_type,
            "before": manifest_diff.before,
            "after": manifest_diff.after,
            "requires_human_approval": (
                manifest_diff.requires_human_approval
            ),
            "writes_file": manifest_diff.writes_file,
        },
        "patch_proposal": {
            "incident_type": patch_proposal.incident_type,
            "target_file": patch_proposal.target_file,
            "container_name": patch_proposal.container_name,
            "field": patch_proposal.field,
            "current_value": patch_proposal.current_value,
            "proposed_value": patch_proposal.proposed_value,
            "reason": patch_proposal.reason,
            "requires_human_approval": (
                patch_proposal.requires_human_approval
            ),
            "writes_file": patch_proposal.writes_file,
        },
        "candidate_value": {
            "incident_type": candidate_value.incident_type,
            "field": candidate_value.field,
            "current_value": candidate_value.current_value,
            "candidate_value": candidate_value.candidate_value,
            "reason": candidate_value.reason,
            "confidence": candidate_value.confidence,
            "requires_human_approval": (
                candidate_value.requires_human_approval
            ),
            "auto_apply": candidate_value.auto_apply,
        },
        "reviewed_patch": {
            "incident_type": reviewed_patch.incident_type,
            "target_file": reviewed_patch.target_file,
            "container_name": reviewed_patch.container_name,
            "field": reviewed_patch.field,
            "current_value": reviewed_patch.current_value,
            "candidate_value": reviewed_patch.candidate_value,
            "approved_value": reviewed_patch.approved_value,
            "reason": reviewed_patch.reason,
            "confidence": reviewed_patch.confidence,
            "requires_human_approval": (
                reviewed_patch.requires_human_approval
            ),
            "ready_for_pr": reviewed_patch.ready_for_pr,
            "writes_file": reviewed_patch.writes_file,
            "auto_apply": reviewed_patch.auto_apply,
        },
    }

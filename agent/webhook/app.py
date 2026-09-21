from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List

from agent.sre_agent.analyzer import analyze_pod


app = FastAPI(
    title="KubePilot SRE Alert Webhook",
    version="0.2.0",
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
    }

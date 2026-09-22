from dataclasses import dataclass
from typing import Optional
from urllib.error import URLError

from agent.mcp_servers.kubernetes import get_pod_incident_context
from agent.mcp_servers.prometheus import get_pod_metrics
from agent.sre_agent.diagnostic import Diagnosis, RuntimeMetrics, diagnose


@dataclass(frozen=True)
class PodAnalysis:
    namespace: str
    pod_name: str
    container_name: str
    diagnosis: Diagnosis
    memory_mib: Optional[float] = None
    cpu_millicores: Optional[float] = None


def analyze_pod(
    namespace: str,
    pod_name: str,
    container_name: str,
    prometheus_url: str = "http://localhost:9092",
) -> PodAnalysis:
    """
    Analyze a Kubernetes pod incident.

    Kubernetes runtime state is the primary source of truth.

    Prometheus metrics are optional enrichment data.
    A missing metric or unavailable Prometheus server must not
    prevent the Kubernetes incident from being diagnosed.
    """

    incident_context = get_pod_incident_context(
        namespace=namespace,
        pod_name=pod_name,
        container_name=container_name,
    )

    metrics: Optional[RuntimeMetrics] = None

    try:
        pod_metrics = get_pod_metrics(
            pod_pattern=pod_name,
            namespace=namespace,
            base_url=prometheus_url,
        )

        metrics = RuntimeMetrics(
            memory_mib=pod_metrics.memory_mib,
            cpu_millicores=pod_metrics.cpu_millicores,
        )

    except (RuntimeError, URLError):
        # Prometheus is enrichment only.
        # Continue the diagnosis using Kubernetes state.
        metrics = None

    diagnosis = diagnose(
        context=incident_context,
        metrics=metrics,
    )

    return PodAnalysis(
        namespace=namespace,
        pod_name=pod_name,
        container_name=container_name,
        diagnosis=diagnosis,
        memory_mib=(
            metrics.memory_mib
            if metrics is not None
            else None
        ),
        cpu_millicores=(
            metrics.cpu_millicores
            if metrics is not None
            else None
        ),
    )

from dataclasses import dataclass
from typing import Optional

from agent.mcp_servers.kubernetes import get_pod_incident_context
from agent.mcp_servers.prometheus import get_pod_metrics
from agent.sre_agent.diagnostic import Diagnosis, RuntimeMetrics, diagnose


@dataclass(frozen=True)
class PodAnalysis:
    namespace: str
    pod_name: str
    container_name: str
    diagnosis: Diagnosis
    memory_mib: Optional[float]
    cpu_millicores: Optional[float]


def analyze_pod(
    namespace: str,
    pod_name: str,
    container_name: str,
    prometheus_url: str = "http://localhost:9092",
) -> PodAnalysis:
    """
    Analyze a Kubernetes pod using read-only Kubernetes data
    and Prometheus metrics when available.

    Metrics are optional because some incidents, such as
    ImagePullBackOff, may occur before the container ever starts.
    """

    context = get_pod_incident_context(
        namespace=namespace,
        pod_name=pod_name,
        container_name=container_name,
    )

    pod_metrics = None
    runtime_metrics = None

    try:
        pod_metrics = get_pod_metrics(
            pod_pattern=pod_name,
            namespace=namespace,
            base_url=prometheus_url,
        )

        runtime_metrics = RuntimeMetrics(
            memory_mib=pod_metrics.memory_mib,
            cpu_millicores=pod_metrics.cpu_millicores,
        )

    except RuntimeError:
        # Some incidents happen before the container starts,
        # so Prometheus may not have CPU or memory metrics yet.
        pass

    result = diagnose(
        context=context,
        metrics=runtime_metrics,
    )

    return PodAnalysis(
        namespace=namespace,
        pod_name=pod_name,
        container_name=container_name,
        diagnosis=result,
        memory_mib=pod_metrics.memory_mib if pod_metrics else None,
        cpu_millicores=pod_metrics.cpu_millicores if pod_metrics else None,
    )

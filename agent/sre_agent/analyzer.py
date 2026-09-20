
from dataclasses import dataclass

from agent.mcp_servers.kubernetes import get_pod_incident_context
from agent.mcp_servers.prometheus import get_pod_metrics
from agent.sre_agent.diagnostic import Diagnosis, RuntimeMetrics, diagnose


@dataclass(frozen=True)
class PodAnalysis:
    namespace: str
    pod_name: str
    container_name: str
    diagnosis: Diagnosis
    memory_mib: float
    cpu_millicores: float


def analyze_pod(
    namespace: str,
    pod_name: str,
    container_name: str,
    prometheus_url: str = "http://localhost:9092",
) -> PodAnalysis:
    """
    Analyze a Kubernetes pod using read-only Kubernetes data
    and Prometheus metrics.
    """

    context = get_pod_incident_context(
        namespace=namespace,
        pod_name=pod_name,
        container_name=container_name,
    )

    pod_pattern = pod_name

    pod_metrics = get_pod_metrics(
        pod_pattern=pod_pattern,
        namespace=namespace,
        base_url=prometheus_url,
    )

    runtime_metrics = RuntimeMetrics(
        memory_mib=pod_metrics.memory_mib,
        cpu_millicores=pod_metrics.cpu_millicores,
    )

    result = diagnose(
        context=context,
        metrics=runtime_metrics,
    )

    return PodAnalysis(
        namespace=namespace,
        pod_name=pod_name,
        container_name=container_name,
        diagnosis=result,
        memory_mib=pod_metrics.memory_mib,
        cpu_millicores=pod_metrics.cpu_millicores,
    )

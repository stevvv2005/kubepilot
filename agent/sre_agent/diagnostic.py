from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class IncidentContext:
    namespace: str
    pod_name: str
    container_name: str
    waiting_reason: Optional[str] = None
    terminated_reason: Optional[str] = None
    restart_count: int = 0
    readiness_failed: bool = False


@dataclass(frozen=True)
class RuntimeMetrics:
    memory_mib: Optional[float] = None
    cpu_millicores: Optional[float] = None


@dataclass(frozen=True)
class Diagnosis:
    incident_type: str
    root_cause: str
    recommendation: str
    confidence: str


def diagnose(
    context: IncidentContext,
    metrics: Optional[RuntimeMetrics] = None,
) -> Diagnosis:
    """Diagnose a Kubernetes incident without modifying the cluster."""

    if context.terminated_reason == "OOMKilled":
        memory_info = ""

        if metrics and metrics.memory_mib is not None:
            memory_info = (
                f" Recent memory usage is approximately "
                f"{metrics.memory_mib:.2f} MiB."
            )

        return Diagnosis(
            incident_type="OOMKilled",
            root_cause=(
                f"Container '{context.container_name}' in pod "
                f"'{context.pod_name}' exceeded its memory limit."
                f"{memory_info}"
            ),
            recommendation=(
                "Review recent memory usage and the workload memory limit. "
                "Propose a resource-limit change through Git and a Pull Request."
            ),
            confidence="high",
        )

    if context.waiting_reason == "ImagePullBackOff":
        return Diagnosis(
            incident_type="ImagePullBackOff",
            root_cause=(
                f"Kubernetes cannot pull the image required by container "
                f"'{context.container_name}'."
            ),
            recommendation=(
                "Verify the image name, tag, registry availability, "
                "and imagePullSecrets. Apply any correction through Git/PR."
            ),
            confidence="high",
        )

    if context.readiness_failed:
        return Diagnosis(
            incident_type="ReadinessProbeFailed",
            root_cause=(
                f"Container '{context.container_name}' is running but "
                "its readiness probe is failing."
            ),
            recommendation=(
                "Inspect the readiness probe configuration and application logs. "
                "Propose configuration changes through Git/PR."
            ),
            confidence="medium",
        )

    if (
        context.waiting_reason is None
        and context.terminated_reason is None
        and not context.readiness_failed
    ):
        return Diagnosis(
            incident_type="Healthy",
            root_cause="No active Kubernetes incident was detected.",
            recommendation="No corrective action is required.",
            confidence="high",
        )

    return Diagnosis(
        incident_type="Unknown",
        root_cause="The available evidence is insufficient for a known diagnosis.",
        recommendation=(
            "Collect pod description, Kubernetes events, container logs, "
            "and recent Prometheus metrics before proposing any action."
        ),
        confidence="low",
    )

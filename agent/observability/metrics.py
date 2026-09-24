from threading import Lock
from typing import Dict


class KubePilotMetrics:
    """Small in-memory Prometheus-compatible metrics registry."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: Dict[str, int] = {
            "kubepilot_incidents_total": 0,
            "kubepilot_approvals_total": 0,
            "kubepilot_rejections_total": 0,
            "kubepilot_prs_created_total": 0,
            "kubepilot_github_execution_failures_total": 0,
            "kubepilot_slack_callbacks_total": 0,
            "kubepilot_llm_requests_total": 0,
        }

    def increment(self, metric_name: str, value: int = 1) -> None:
        if metric_name not in self._counters:
            raise ValueError(f"Unknown metric: {metric_name}")

        with self._lock:
            self._counters[metric_name] += value

    def snapshot(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._counters)

    def render_prometheus(self) -> str:
        snapshot = self.snapshot()

        lines = []
        for name, value in snapshot.items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")

        return "\n".join(lines) + "\n"


kubepilot_metrics = KubePilotMetrics()

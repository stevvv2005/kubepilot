import json
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import urlopen


@dataclass(frozen=True)
class PrometheusQueryResult:
    status: str
    result_type: str
    result: list


class PrometheusClient:
    def __init__(self, base_url: str = "http://localhost:9092") -> None:
        self.base_url = base_url.rstrip("/")

    def query(self, promql: str) -> PrometheusQueryResult:
        """
        Execute a read-only Prometheus instant query.
        """

        params = urlencode({"query": promql})
        url = f"{self.base_url}/api/v1/query?{params}"

        with urlopen(url, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))

        if payload.get("status") != "success":
            raise RuntimeError(
                f"Prometheus query failed: {payload}"
            )

        data = payload.get("data", {})

        return PrometheusQueryResult(
            status=payload["status"],
            result_type=data.get("resultType", ""),
            result=data.get("result", []),
        )


@dataclass(frozen=True)
class PodMetrics:
    memory_bytes: float
    memory_mib: float
    cpu_cores: float
    cpu_millicores: float


def get_pod_metrics(
    pod_pattern: str,
    namespace: str = "default",
    base_url: str = "http://localhost:9092",
) -> PodMetrics:
    client = PrometheusClient(base_url)

    memory_query = (
        'sum(container_memory_working_set_bytes'
        f'{{namespace="{namespace}",pod=~"{pod_pattern}",container!=""}})'
    )

    cpu_query = (
        'sum(rate(container_cpu_usage_seconds_total'
        f'{{namespace="{namespace}",pod=~"{pod_pattern}",container!=""}}[5m]))'
    )

    memory_result = client.query(memory_query)
    cpu_result = client.query(cpu_query)

    if not memory_result.result:
        raise RuntimeError("No memory metrics returned by Prometheus")

    if not cpu_result.result:
        raise RuntimeError("No CPU metrics returned by Prometheus")

    memory_bytes = float(memory_result.result[0]["value"][1])
    cpu_cores = float(cpu_result.result[0]["value"][1])

    return PodMetrics(
        memory_bytes=memory_bytes,
        memory_mib=memory_bytes / (1024 * 1024),
        cpu_cores=cpu_cores,
        cpu_millicores=cpu_cores * 1000,
    )

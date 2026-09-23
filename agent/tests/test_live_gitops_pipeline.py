from pathlib import Path

from agent.finops_agent.live_gitops_pipeline import (
    generate_live_gitops_pipeline,
)
from agent.finops_agent.opencost_client import (
    OpenCostClient,
)


class FakeOpenCostClient(OpenCostClient):
    def get_allocations(
        self,
        window: str = "1h",
        aggregate: str = "namespace,pod",
    ):
        return {
            "data": [
                {
                    "default/checkoutservice": {
                        "properties": {
                            "namespace": "default",
                            "controller": "checkoutservice",
                            "controllerKind": "Deployment",
                            "pod": "checkoutservice-abc123",
                        },
                        "minutes": 60,
                        "cpuCoreRequestAverage": 0.1,
                        "cpuCoreUsageAverage": 0.01,
                        "ramByteRequestAverage": 67108864,
                        "ramByteUsageAverage": 8388608,
                        "cpuCost": 0.002,
                        "ramCost": 0.001,
                    },
                    "default/frontend": {
                        "properties": {
                            "namespace": "default",
                            "controller": "frontend",
                            "controllerKind": "Deployment",
                            "pod": "frontend-abc123",
                        },
                        "minutes": 60,
                        "cpuCoreRequestAverage": 0.1,
                        "cpuCoreUsageAverage": 0.02,
                        "ramByteRequestAverage": 67108864,
                        "ramByteUsageAverage": 10485760,
                        "cpuCost": 0.002,
                        "ramCost": 0.001,
                    },
                    "default/cartservice": {
                        "properties": {
                            "namespace": "default",
                            "controller": "cartservice",
                            "controllerKind": "Deployment",
                            "pod": "cartservice-abc123",
                        },
                        "minutes": 60,
                        "cpuCoreRequestAverage": 0.2,
                        "cpuCoreUsageAverage": 0.15,
                        "ramByteRequestAverage": 67108864,
                        "ramByteUsageAverage": 58720256,
                        "cpuCost": 0.003,
                        "ramCost": 0.002,
                    },
                }
            ]
        }


def _write_gitops_manifest(
    repository_root: Path,
) -> None:
    target = (
        repository_root
        / "gitops"
        / "apps"
        / "online-boutique"
        / "base"
        / "kubernetes-manifests.yaml"
    )

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    target.write_text(
        """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: checkoutservice
spec:
  template:
    spec:
      containers:
        - name: server
          resources:
            requests:
              cpu: 100m
              memory: 64Mi
            limits:
              cpu: 200m
              memory: 128Mi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
spec:
  template:
    spec:
      containers:
        - name: server
          resources:
            requests:
              cpu: 100m
              memory: 64Mi
            limits:
              cpu: 200m
              memory: 128Mi
""".strip(),
        encoding="utf-8",
    )


def test_live_gitops_pipeline(
    tmp_path,
):
    _write_gitops_manifest(
        tmp_path,
    )

    client = FakeOpenCostClient()

    result = generate_live_gitops_pipeline(
        client=client,
        window="1h",
        namespace="default",
        repository_root=str(tmp_path),
    )

    assert result.source == "opencost"
    assert result.namespace_filter == "default"

    assert result.total_workloads == 3

    # checkoutservice + frontend
    assert result.waste_candidates == 2

    assert result.resolved_targets == 2
    assert result.gitops_diffs == 2

    assert len(result.diffs) == 2

    assert result.read_only is True
    assert result.performs_write is False
    assert result.writes_file is False
    assert result.writes_git is False
    assert result.requires_human_approval is True
    assert result.auto_apply is False


def test_pipeline_generates_expected_checkout_diff(
    tmp_path,
):
    _write_gitops_manifest(
        tmp_path,
    )

    result = generate_live_gitops_pipeline(
        client=FakeOpenCostClient(),
        namespace="default",
        repository_root=str(tmp_path),
    )

    checkout_diff = next(
        diff
        for diff in result.diffs
        if diff.manifest_name
        == "checkoutservice"
    )

    assert (
        checkout_diff.container_name
        == "server"
    )

    assert (
        checkout_diff.current_cpu_request
        == "100m"
    )

    assert (
        checkout_diff.proposed_cpu_request
        == "20m"
    )

    assert (
        checkout_diff.current_memory_request
        == "64Mi"
    )

    assert (
        checkout_diff.proposed_memory_request
        == "16Mi"
    )

    assert (
        checkout_diff.requires_human_approval
        is True
    )

    assert checkout_diff.writes_file is False
    assert checkout_diff.writes_git is False
    assert checkout_diff.auto_apply is False


def test_pipeline_ignores_non_waste_workloads(
    tmp_path,
):
    _write_gitops_manifest(
        tmp_path,
    )

    result = generate_live_gitops_pipeline(
        client=FakeOpenCostClient(),
        namespace="default",
        repository_root=str(tmp_path),
    )

    names = {
        diff.manifest_name
        for diff in result.diffs
    }

    assert "cartservice" not in names


def test_pipeline_preserves_gitops_target(
    tmp_path,
):
    _write_gitops_manifest(
        tmp_path,
    )

    result = generate_live_gitops_pipeline(
        client=FakeOpenCostClient(),
        namespace="default",
        repository_root=str(tmp_path),
    )

    for diff in result.diffs:
        assert (
            diff.target_file
            == (
                "gitops/apps/online-boutique/base/"
                "kubernetes-manifests.yaml"
            )
        )


def test_pipeline_is_strictly_read_only(
    tmp_path,
):
    _write_gitops_manifest(
        tmp_path,
    )

    target = (
        tmp_path
        / "gitops"
        / "apps"
        / "online-boutique"
        / "base"
        / "kubernetes-manifests.yaml"
    )

    before = target.read_text(
        encoding="utf-8",
    )

    result = generate_live_gitops_pipeline(
        client=FakeOpenCostClient(),
        namespace="default",
        repository_root=str(tmp_path),
    )

    after = target.read_text(
        encoding="utf-8",
    )

    assert before == after

    assert result.read_only is True
    assert result.performs_write is False
    assert result.writes_file is False
    assert result.writes_git is False
    assert result.auto_apply is False
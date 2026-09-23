from pathlib import Path

import pytest

from agent.finops_agent.manifest_inspector import (
    inspect_finops_manifest,
)
from agent.finops_agent.target_file_resolver import (
    FinOpsTargetResolution,
)


def _write_manifest(
    repository_root: Path,
) -> str:
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
apiVersion: v1
kind: Service
metadata:
  name: checkoutservice
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: checkoutservice
spec:
  template:
    spec:
      containers:
        - name: server
          image: example/checkout:1
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
  name: redis-cart
spec:
  template:
    spec:
      containers:
        - name: redis
          image: redis:alpine
          resources:
            limits:
              memory: 256Mi
              cpu: 125m
            requests:
              cpu: 70m
              memory: 200Mi
""".strip(),
        encoding="utf-8",
    )

    return (
        "gitops/apps/online-boutique/base/"
        "kubernetes-manifests.yaml"
    )


def _resolution(
    target_file: str,
    manifest_name: str,
) -> FinOpsTargetResolution:
    return FinOpsTargetResolution(
        namespace="default",
        workload_name=manifest_name,
        workload_base_name=manifest_name,
        target_file=target_file,
        manifest_kind="Deployment",
        manifest_name=manifest_name,
        matched=True,
        reason="test",
        read_only=True,
        performs_write=False,
    )


def test_inspect_checkoutservice_resources(
    tmp_path,
):
    target_file = _write_manifest(
        tmp_path,
    )

    resolution = _resolution(
        target_file=target_file,
        manifest_name="checkoutservice",
    )

    state = inspect_finops_manifest(
        resolution=resolution,
        repository_root=str(tmp_path),
    )

    assert state.found is True

    assert (
        state.container_name
        == "server"
    )

    assert state.cpu_request == "100m"
    assert state.memory_request == "64Mi"

    assert state.cpu_limit == "200m"
    assert state.memory_limit == "128Mi"

    assert state.read_only is True
    assert state.performs_write is False


def test_inspect_redis_cart_resources(
    tmp_path,
):
    target_file = _write_manifest(
        tmp_path,
    )

    resolution = _resolution(
        target_file=target_file,
        manifest_name="redis-cart",
    )

    state = inspect_finops_manifest(
        resolution=resolution,
        repository_root=str(tmp_path),
    )

    assert state.found is True

    assert (
        state.container_name
        == "redis"
    )

    assert state.cpu_request == "70m"
    assert state.memory_request == "200Mi"

    assert state.cpu_limit == "125m"
    assert state.memory_limit == "256Mi"


def test_selects_deployment_not_service(
    tmp_path,
):
    target_file = _write_manifest(
        tmp_path,
    )

    resolution = _resolution(
        target_file=target_file,
        manifest_name="checkoutservice",
    )

    state = inspect_finops_manifest(
        resolution=resolution,
        repository_root=str(tmp_path),
    )

    assert state.manifest_kind == "Deployment"
    assert state.container_name == "server"


def test_unknown_manifest_returns_not_found(
    tmp_path,
):
    target_file = _write_manifest(
        tmp_path,
    )

    resolution = _resolution(
        target_file=target_file,
        manifest_name="does-not-exist",
    )

    state = inspect_finops_manifest(
        resolution=resolution,
        repository_root=str(tmp_path),
    )

    assert state.found is False
    assert state.container_name == ""

    assert (
        "not found"
        in state.reason
    )


def test_unresolved_target_is_rejected(
    tmp_path,
):
    resolution = FinOpsTargetResolution(
        namespace="default",
        workload_name="checkoutservice",
        workload_base_name=None,
        target_file=None,
        manifest_kind=None,
        manifest_name=None,
        matched=False,
        reason="not allowlisted",
        read_only=True,
        performs_write=False,
    )

    with pytest.raises(
        ValueError,
        match="unresolved",
    ):
        inspect_finops_manifest(
            resolution=resolution,
            repository_root=str(tmp_path),
        )


def test_target_path_cannot_escape_repository(
    tmp_path,
):
    resolution = _resolution(
        target_file="../secret.yaml",
        manifest_name="checkoutservice",
    )

    with pytest.raises(
        ValueError,
        match="escapes repository root",
    ):
        inspect_finops_manifest(
            resolution=resolution,
            repository_root=str(tmp_path),
        )


def test_missing_target_file_is_rejected(
    tmp_path,
):
    resolution = _resolution(
        target_file="missing.yaml",
        manifest_name="checkoutservice",
    )

    with pytest.raises(
        ValueError,
        match="does not exist",
    ):
        inspect_finops_manifest(
            resolution=resolution,
            repository_root=str(tmp_path),
        )


def test_multiple_containers_are_not_selected_automatically(
    tmp_path,
):
    target = (
        tmp_path
        / "multi.yaml"
    )

    target.write_text(
        """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: multi
spec:
  template:
    spec:
      containers:
        - name: app
          resources:
            requests:
              cpu: 100m
        - name: sidecar
          resources:
            requests:
              cpu: 50m
""".strip(),
        encoding="utf-8",
    )

    resolution = _resolution(
        target_file="multi.yaml",
        manifest_name="multi",
    )

    state = inspect_finops_manifest(
        resolution=resolution,
        repository_root=str(tmp_path),
    )

    assert state.found is False

    assert (
        "multiple containers"
        in state.reason
    )


def test_inspection_does_not_modify_manifest(
    tmp_path,
):
    target_file = _write_manifest(
        tmp_path,
    )

    target_path = (
        tmp_path
        / target_file
    )

    before = target_path.read_text(
        encoding="utf-8",
    )

    resolution = _resolution(
        target_file=target_file,
        manifest_name="checkoutservice",
    )

    inspect_finops_manifest(
        resolution=resolution,
        repository_root=str(tmp_path),
    )

    after = target_path.read_text(
        encoding="utf-8",
    )

    assert after == before

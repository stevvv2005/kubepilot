from pathlib import Path

import pytest
import yaml

from agent.finops_agent.approved_manifest import (
    render_approved_finops_manifest,
)
from agent.finops_agent.human_approval import (
    ApprovedFinOpsChange,
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
            requests:
              cpu: 70m
              memory: 200Mi
            limits:
              cpu: 125m
              memory: 256Mi
""".strip(),
        encoding="utf-8",
    )

    return (
        "gitops/apps/online-boutique/base/"
        "kubernetes-manifests.yaml"
    )


def _approved_change(
    target_file: str,
    cpu: str | None = "50m",
    memory: str | None = "32Mi",
) -> ApprovedFinOpsChange:
    return ApprovedFinOpsChange(
        namespace="default",
        workload_name="checkoutservice",
        workload_type="Deployment",
        target_file=target_file,
        manifest_kind="Deployment",
        manifest_name="checkoutservice",
        container_name="server",
        current_cpu_request="100m",
        proposed_cpu_request="10m",
        approved_cpu_request=cpu,
        current_memory_request="64Mi",
        proposed_memory_request="16Mi",
        approved_memory_request=memory,
        estimated_monthly_savings_usd=0.62,
        approved=True,
        reviewer="alice",
        reason="Use conservative approved values",
        ready_for_render=True,
        requires_human_approval=True,
        writes_file=False,
        writes_git=False,
        auto_apply=False,
    )


def test_render_approved_finops_manifest(
    tmp_path,
):
    target_file = _write_manifest(
        tmp_path,
    )

    result = render_approved_finops_manifest(
        approved_change=_approved_change(
            target_file,
        ),
        repository_root=str(tmp_path),
    )

    assert result.ready_for_commit is True
    assert result.writes_file is False
    assert result.writes_git is False

    documents = list(
        yaml.safe_load_all(
            result.rendered_yaml,
        )
    )

    deployment = next(
        document
        for document in documents
        if isinstance(document, dict)
        and document.get("kind")
        == "Deployment"
        and document.get(
            "metadata",
            {},
        ).get("name")
        == "checkoutservice"
    )

    container = (
        deployment["spec"]
        ["template"]
        ["spec"]
        ["containers"][0]
    )

    requests = container[
        "resources"
    ][
        "requests"
    ]

    assert requests["cpu"] == "50m"
    assert requests["memory"] == "32Mi"

    assert (
        container["resources"]["limits"]["cpu"]
        == "200m"
    )

    assert (
        container["resources"]["limits"]["memory"]
        == "128Mi"
    )


def test_render_cpu_only(
    tmp_path,
):
    target_file = _write_manifest(
        tmp_path,
    )

    result = render_approved_finops_manifest(
        approved_change=_approved_change(
            target_file,
            cpu="40m",
            memory=None,
        ),
        repository_root=str(tmp_path),
    )

    documents = list(
        yaml.safe_load_all(
            result.rendered_yaml,
        )
    )

    deployment = next(
        document
        for document in documents
        if isinstance(document, dict)
        and document.get("kind")
        == "Deployment"
        and document.get(
            "metadata",
            {},
        ).get("name")
        == "checkoutservice"
    )

    requests = (
        deployment["spec"]
        ["template"]
        ["spec"]
        ["containers"][0]
        ["resources"]
        ["requests"]
    )

    assert requests["cpu"] == "40m"
    assert requests["memory"] == "64Mi"


def test_render_memory_only(
    tmp_path,
):
    target_file = _write_manifest(
        tmp_path,
    )

    result = render_approved_finops_manifest(
        approved_change=_approved_change(
            target_file,
            cpu=None,
            memory="48Mi",
        ),
        repository_root=str(tmp_path),
    )

    documents = list(
        yaml.safe_load_all(
            result.rendered_yaml,
        )
    )

    deployment = next(
        document
        for document in documents
        if isinstance(document, dict)
        and document.get("kind")
        == "Deployment"
        and document.get(
            "metadata",
            {},
        ).get("name")
        == "checkoutservice"
    )

    requests = (
        deployment["spec"]
        ["template"]
        ["spec"]
        ["containers"][0]
        ["resources"]
        ["requests"]
    )

    assert requests["cpu"] == "100m"
    assert requests["memory"] == "48Mi"


def test_render_does_not_modify_original_file(
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

    render_approved_finops_manifest(
        approved_change=_approved_change(
            target_file,
        ),
        repository_root=str(tmp_path),
    )

    after = target_path.read_text(
        encoding="utf-8",
    )

    assert after == before


def test_rejected_change_is_rejected(
    tmp_path,
):
    target_file = _write_manifest(
        tmp_path,
    )

    change = _approved_change(
        target_file,
    )

    rejected = ApprovedFinOpsChange(
        namespace=change.namespace,
        workload_name=change.workload_name,
        workload_type=change.workload_type,
        target_file=change.target_file,
        manifest_kind=change.manifest_kind,
        manifest_name=change.manifest_name,
        container_name=change.container_name,
        current_cpu_request=change.current_cpu_request,
        proposed_cpu_request=change.proposed_cpu_request,
        approved_cpu_request=None,
        current_memory_request=change.current_memory_request,
        proposed_memory_request=change.proposed_memory_request,
        approved_memory_request=None,
        estimated_monthly_savings_usd=(
            change.estimated_monthly_savings_usd
        ),
        approved=False,
        reviewer="alice",
        reason="rejected",
        ready_for_render=False,
        requires_human_approval=True,
        writes_file=False,
        writes_git=False,
        auto_apply=False,
    )

    with pytest.raises(
        ValueError,
        match="explicitly approved",
    ):
        render_approved_finops_manifest(
            approved_change=rejected,
            repository_root=str(tmp_path),
        )


def test_target_file_must_exist(
    tmp_path,
):
    with pytest.raises(
        ValueError,
        match="does not exist",
    ):
        render_approved_finops_manifest(
            approved_change=_approved_change(
                "missing.yaml",
            ),
            repository_root=str(tmp_path),
        )


def test_target_cannot_escape_repository(
    tmp_path,
):
    with pytest.raises(
        ValueError,
        match="escapes repository root",
    ):
        render_approved_finops_manifest(
            approved_change=_approved_change(
                "../secret.yaml",
            ),
            repository_root=str(tmp_path),
        )


def test_wrong_manifest_name_is_rejected(
    tmp_path,
):
    target_file = _write_manifest(
        tmp_path,
    )

    change = _approved_change(
        target_file,
    )

    invalid = ApprovedFinOpsChange(
        namespace=change.namespace,
        workload_name=change.workload_name,
        workload_type=change.workload_type,
        target_file=change.target_file,
        manifest_kind=change.manifest_kind,
        manifest_name="does-not-exist",
        container_name=change.container_name,
        current_cpu_request=change.current_cpu_request,
        proposed_cpu_request=change.proposed_cpu_request,
        approved_cpu_request=change.approved_cpu_request,
        current_memory_request=change.current_memory_request,
        proposed_memory_request=change.proposed_memory_request,
        approved_memory_request=change.approved_memory_request,
        estimated_monthly_savings_usd=(
            change.estimated_monthly_savings_usd
        ),
        approved=True,
        reviewer="alice",
        reason="test",
        ready_for_render=True,
        requires_human_approval=True,
        writes_file=False,
        writes_git=False,
        auto_apply=False,
    )

    with pytest.raises(
        ValueError,
        match="target was not found",
    ):
        render_approved_finops_manifest(
            approved_change=invalid,
            repository_root=str(tmp_path),
        )


def test_wrong_container_is_rejected(
    tmp_path,
):
    target_file = _write_manifest(
        tmp_path,
    )

    change = _approved_change(
        target_file,
    )

    invalid = ApprovedFinOpsChange(
        namespace=change.namespace,
        workload_name=change.workload_name,
        workload_type=change.workload_type,
        target_file=change.target_file,
        manifest_kind=change.manifest_kind,
        manifest_name=change.manifest_name,
        container_name="wrong-container",
        current_cpu_request=change.current_cpu_request,
        proposed_cpu_request=change.proposed_cpu_request,
        approved_cpu_request=change.approved_cpu_request,
        current_memory_request=change.current_memory_request,
        proposed_memory_request=change.proposed_memory_request,
        approved_memory_request=change.approved_memory_request,
        estimated_monthly_savings_usd=(
            change.estimated_monthly_savings_usd
        ),
        approved=True,
        reviewer="alice",
        reason="test",
        ready_for_render=True,
        requires_human_approval=True,
        writes_file=False,
        writes_git=False,
        auto_apply=False,
    )

    with pytest.raises(
        ValueError,
        match="container was not found",
    ):
        render_approved_finops_manifest(
            approved_change=invalid,
            repository_root=str(tmp_path),
        )
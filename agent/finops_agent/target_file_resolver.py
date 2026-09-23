from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Optional


ONLINE_BOUTIQUE_MANIFEST = (
    "gitops/apps/online-boutique/base/"
    "kubernetes-manifests.yaml"
)


ALLOWED_WORKLOADS = {
    "checkoutservice": {
        "kind": "Deployment",
        "name": "checkoutservice",
    },
    "frontend": {
        "kind": "Deployment",
        "name": "frontend",
    },
    "loadgenerator": {
        "kind": "Deployment",
        "name": "loadgenerator",
    },
    "productcatalogservice": {
        "kind": "Deployment",
        "name": "productcatalogservice",
    },
    "recommendationservice": {
        "kind": "Deployment",
        "name": "recommendationservice",
    },
    "redis-cart": {
        "kind": "Deployment",
        "name": "redis-cart",
    },
    "shippingservice": {
        "kind": "Deployment",
        "name": "shippingservice",
    },
}


@dataclass(frozen=True)
class FinOpsTargetResolution:
    namespace: str
    workload_name: str

    workload_base_name: Optional[str]

    target_file: Optional[str]
    manifest_kind: Optional[str]
    manifest_name: Optional[str]

    matched: bool
    reason: str

    read_only: bool = True
    performs_write: bool = False


def _is_safe_repo_relative_path(
    path: str,
) -> bool:
    if not path:
        return False

    candidate = PurePosixPath(path)

    if candidate.is_absolute():
        return False

    if ".." in candidate.parts:
        return False

    return True


def _match_workload_base_name(
    workload_name: str,
) -> Optional[str]:
    """
    Match a live Kubernetes pod/workload name to an
    allowlisted GitOps workload.

    Examples:

    checkoutservice-78b6bcbcc7-s9s22
        -> checkoutservice

    redis-cart-788fbddc7-56qkq
        -> redis-cart
    """

    for base_name in ALLOWED_WORKLOADS:
        if workload_name == base_name:
            return base_name

        if workload_name.startswith(
            f"{base_name}-"
        ):
            return base_name

    return None


def resolve_finops_target(
    namespace: str,
    workload_name: str,
) -> FinOpsTargetResolution:
    """
    Resolve a live FinOps workload to an allowlisted
    GitOps manifest target.

    This function performs no filesystem, Git,
    Kubernetes, or cloud write.
    """

    if namespace != "default":
        return FinOpsTargetResolution(
            namespace=namespace,
            workload_name=workload_name,
            workload_base_name=None,
            target_file=None,
            manifest_kind=None,
            manifest_name=None,
            matched=False,
            reason=(
                "Namespace is not allowlisted for "
                "Online Boutique FinOps changes."
            ),
        )

    base_name = _match_workload_base_name(
        workload_name,
    )

    if base_name is None:
        return FinOpsTargetResolution(
            namespace=namespace,
            workload_name=workload_name,
            workload_base_name=None,
            target_file=None,
            manifest_kind=None,
            manifest_name=None,
            matched=False,
            reason=(
                "Workload is not allowlisted for "
                "FinOps GitOps changes."
            ),
        )

    workload_config = ALLOWED_WORKLOADS[
        base_name
    ]

    target_file = ONLINE_BOUTIQUE_MANIFEST

    if not _is_safe_repo_relative_path(
        target_file,
    ):
        return FinOpsTargetResolution(
            namespace=namespace,
            workload_name=workload_name,
            workload_base_name=base_name,
            target_file=None,
            manifest_kind=None,
            manifest_name=None,
            matched=False,
            reason=(
                "Resolved target path failed "
                "repository safety validation."
            ),
        )

    return FinOpsTargetResolution(
        namespace=namespace,
        workload_name=workload_name,
        workload_base_name=base_name,
        target_file=target_file,
        manifest_kind=workload_config[
            "kind"
        ],
        manifest_name=workload_config[
            "name"
        ],
        matched=True,
        reason=(
            "Workload matched the allowlisted "
            "Online Boutique GitOps manifest."
        ),
        read_only=True,
        performs_write=False,
    )

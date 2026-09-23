from agent.finops_agent.target_file_resolver import (
    ONLINE_BOUTIQUE_MANIFEST,
    _is_safe_repo_relative_path,
    resolve_finops_target,
)


def test_resolve_checkoutservice_pod():
    result = resolve_finops_target(
        namespace="default",
        workload_name=(
            "checkoutservice-78b6bcbcc7-s9s22"
        ),
    )

    assert result.matched is True

    assert (
        result.workload_base_name
        == "checkoutservice"
    )

    assert (
        result.target_file
        == ONLINE_BOUTIQUE_MANIFEST
    )

    assert result.manifest_kind == "Deployment"

    assert (
        result.manifest_name
        == "checkoutservice"
    )

    assert result.read_only is True
    assert result.performs_write is False


def test_resolve_redis_cart_pod():
    result = resolve_finops_target(
        namespace="default",
        workload_name=(
            "redis-cart-788fbddc7-56qkq"
        ),
    )

    assert result.matched is True

    assert (
        result.workload_base_name
        == "redis-cart"
    )

    assert (
        result.manifest_name
        == "redis-cart"
    )


def test_all_current_finops_candidates_are_allowlisted():
    workload_names = [
        "checkoutservice-78b6bcbcc7-s9s22",
        "frontend-58b4dc4d4d-hg2f8",
        "loadgenerator-5985dc76b-srrkh",
        "productcatalogservice-67944c9df7-8wg55",
        "recommendationservice-5887f9f797-jzxkm",
        "redis-cart-788fbddc7-56qkq",
        "shippingservice-7ff767d68f-rqtdw",
    ]

    for workload_name in workload_names:
        result = resolve_finops_target(
            namespace="default",
            workload_name=workload_name,
        )

        assert result.matched is True

        assert (
            result.target_file
            == ONLINE_BOUTIQUE_MANIFEST
        )

        assert (
            result.manifest_kind
            == "Deployment"
        )


def test_exact_workload_name_is_supported():
    result = resolve_finops_target(
        namespace="default",
        workload_name="frontend",
    )

    assert result.matched is True
    assert result.manifest_name == "frontend"


def test_unknown_workload_is_rejected():
    result = resolve_finops_target(
        namespace="default",
        workload_name="unknown-service-abc123",
    )

    assert result.matched is False
    assert result.target_file is None
    assert result.manifest_name is None

    assert (
        "not allowlisted"
        in result.reason
    )


def test_non_default_namespace_is_rejected():
    result = resolve_finops_target(
        namespace="monitoring",
        workload_name=(
            "prometheus-server-123"
        ),
    )

    assert result.matched is False
    assert result.target_file is None

    assert (
        "Namespace is not allowlisted"
        in result.reason
    )


def test_safe_gitops_target_path():
    assert (
        _is_safe_repo_relative_path(
            ONLINE_BOUTIQUE_MANIFEST
        )
        is True
    )


def test_parent_traversal_path_is_rejected():
    assert (
        _is_safe_repo_relative_path(
            "../secret.yaml"
        )
        is False
    )


def test_nested_parent_traversal_is_rejected():
    assert (
        _is_safe_repo_relative_path(
            "gitops/apps/../../secret.yaml"
        )
        is False
    )

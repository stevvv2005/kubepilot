from agent.sre_agent.target_file_resolver import (
    _is_safe_repo_path,
    resolve_target_file,
)


def test_resolve_oomkilled_target_file():
    result = resolve_target_file(
        namespace="default",
        pod_name="kubepilot-oomkilled",
        container_name="memory-hog",
    )

    assert result.matched is True
    assert result.target_file == "chaos/oomkilled-pod.yaml"
    assert "allowlist" in result.reason


def test_resolve_imagepullbackoff_target_file():
    result = resolve_target_file(
        namespace="default",
        pod_name="kubepilot-imagepullbackoff",
        container_name="broken-container",
    )

    assert result.matched is True
    assert result.target_file == "chaos/imagepullbackoff-pod.yaml"


def test_resolve_readiness_target_file():
    result = resolve_target_file(
        namespace="default",
        pod_name="kubepilot-readiness-failed",
        container_name="web",
    )

    assert result.matched is True
    assert result.target_file == "chaos/readiness-failed-pod.yaml"


def test_unknown_workload_is_not_resolved():
    result = resolve_target_file(
        namespace="default",
        pod_name="unknown-pod",
        container_name="unknown-container",
    )

    assert result.matched is False
    assert result.target_file is None


def test_safe_relative_repository_path():
    assert _is_safe_repo_path("chaos/oomkilled-pod.yaml") is True


def test_absolute_path_is_rejected():
    assert _is_safe_repo_path("/etc/passwd") is False


def test_parent_traversal_is_rejected():
    assert _is_safe_repo_path("../secret.txt") is False
    assert _is_safe_repo_path("chaos/../../secret.txt") is False


def test_empty_path_is_rejected():
    assert _is_safe_repo_path("") is False

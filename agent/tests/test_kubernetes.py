import pytest

from agent.mcp_servers.kubernetes import run_kubectl


def test_kubectl_get_is_allowed():
    result = run_kubectl(["get", "pods", "-n", "default"])

    assert result.returncode == 0
    assert "frontend" in result.stdout


def test_kubectl_delete_is_blocked():
    with pytest.raises(ValueError, match="not allowed"):
        run_kubectl(["delete", "pod", "frontend"])


def test_empty_command_is_blocked():
    with pytest.raises(ValueError, match="cannot be empty"):
        run_kubectl([])

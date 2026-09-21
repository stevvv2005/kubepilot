from agent.sre_agent.manifest_inspector import inspect_container


def test_inspect_container_reads_image():
    manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": "demo",
        },
        "spec": {
            "containers": [
                {
                    "name": "app",
                    "image": "nginx:1.27",
                }
            ]
        },
    }

    state = inspect_container(
        manifest=manifest,
        container_name="app",
    )

    assert state.name == "app"
    assert state.image == "nginx:1.27"
    assert state.memory_limit is None
    assert state.readiness_path is None
    assert state.readiness_port is None


def test_inspect_container_reads_memory_limit():
    manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": "memory-test",
        },
        "spec": {
            "containers": [
                {
                    "name": "memory-hog",
                    "image": "python:3.12",
                    "resources": {
                        "limits": {
                            "memory": "32Mi",
                        }
                    },
                }
            ]
        },
    }

    state = inspect_container(
        manifest=manifest,
        container_name="memory-hog",
    )

    assert state.image == "python:3.12"
    assert state.memory_limit == "32Mi"


def test_inspect_container_reads_readiness_probe():
    manifest = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": "frontend",
        },
        "spec": {
            "template": {
                "spec": {
                    "containers": [
                        {
                            "name": "server",
                            "image": "nginx:1.27",
                            "readinessProbe": {
                                "httpGet": {
                                    "path": "/health",
                                    "port": 8080,
                                }
                            },
                        }
                    ]
                }
            }
        },
    }

    state = inspect_container(
        manifest=manifest,
        container_name="server",
    )

    assert state.image == "nginx:1.27"
    assert state.readiness_path == "/health"
    assert state.readiness_port == 8080


def test_inspect_container_raises_when_container_is_missing():
    manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "spec": {
            "containers": [
                {
                    "name": "app",
                    "image": "nginx:1.27",
                }
            ]
        },
    }

    try:
        inspect_container(
            manifest=manifest,
            container_name="missing",
        )
    except ValueError as exc:
        assert "Container not found" in str(exc)
    else:
        raise AssertionError("Expected ValueError")

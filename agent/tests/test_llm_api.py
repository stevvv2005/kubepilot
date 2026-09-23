from fastapi.testclient import TestClient

from agent.webhook.app import app


client = TestClient(app)


def test_llm_analyze_sre():
    response = client.post(
        "/llm/analyze",
        json={
            "query": (
                "Why was the container "
                "OOMKilled because of memory?"
            ),
            "signal_type": "sre_incident",
            "namespace": "default",
            "workload_name": (
                "checkoutservice"
            ),
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert (
        body["signal_type"]
        == "sre_incident"
    )

    assert body["namespace"] == "default"

    assert (
        body["workload_name"]
        == "checkoutservice"
    )

    assert body["rag"]["used"] is True

    assert (
        body["llm"]["provider"]
        == "mock"
    )

    assert (
        body["llm"]["model"]
        == "kubepilot-mock-v1"
    )

    assert (
        body["safety"]
        ["requires_human_approval"]
        is True
    )

    assert (
        body["safety"]
        ["allows_direct_cluster_write"]
        is False
    )

    assert (
        body["safety"]
        ["external_request_performed"]
        is False
    )

    assert (
        body["safety"]
        ["performs_write"]
        is False
    )


def test_llm_analyze_finops():
    response = client.post(
        "/llm/analyze",
        json={
            "query": (
                "Should this workload be "
                "rightsized based on CPU "
                "and memory utilization?"
            ),
            "signal_type": "finops",
            "namespace": "default",
            "workload_name": (
                "checkoutservice"
            ),
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["rag"]["used"] is True

    assert (
        "GitOps"
        in body["llm"]["analysis"]
    )

    assert (
        body["safety"]
        ["performs_write"]
        is False
    )


def test_llm_analyze_without_rag_match():
    response = client.post(
        "/llm/analyze",
        json={
            "query": "unknown xyz abc",
            "signal_type": "sre",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["rag"]["used"] is False
    assert body["rag"]["empty"] is True

    assert (
        body["safety"]
        ["external_request_performed"]
        is False
    )


def test_llm_analyze_rejects_empty_query():
    response = client.post(
        "/llm/analyze",
        json={
            "query": "   ",
            "signal_type": "sre",
        },
    )

    assert response.status_code == 400

    assert (
        "query is required"
        in response.json()["detail"]
    )


def test_llm_analyze_rejects_empty_signal_type():
    response = client.post(
        "/llm/analyze",
        json={
            "query": "OOMKilled memory",
            "signal_type": "   ",
        },
    )

    assert response.status_code == 400

    assert (
        "signal_type is required"
        in response.json()["detail"]
    )
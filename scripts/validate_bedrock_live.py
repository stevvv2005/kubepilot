import os

from agent.llm.bedrock_aws_client import (
    BedrockAWSClientConfig,
    create_bedrock_runtime_adapter,
)
from agent.llm.bedrock_client import (
    BedrockLLMClient,
)
from agent.llm.bedrock_execution_gateway import (
    validate_bedrock_execution,
)
from agent.llm.prompt_builder import (
    build_llm_prompt,
)
from agent.llm.workflow import (
    build_default_knowledge_base,
)
from agent.rag.context_builder import (
    build_rag_context,
)


MODEL_ID = "eu.amazon.nova-micro-v1:0"
REGION = "eu-west-3"


def main() -> None:
    live_authorized = (
        os.getenv(
            "KUBEPILOT_BEDROCK_LIVE_AUTHORIZED",
            "",
        ).strip().lower()
        == "true"
    )

    if not live_authorized:
        raise RuntimeError(
            "Live Bedrock validation is disabled. "
            "Set "
            "KUBEPILOT_BEDROCK_LIVE_AUTHORIZED=true "
            "to explicitly authorize one live test."
        )

    print("KubePilot Bedrock live validation")
    print("---------------------------------")
    print(f"region = {REGION}")
    print(f"model = {MODEL_ID}")

    knowledge_base = (
        build_default_knowledge_base(
            repository_root=".",
        )
    )

    query = (
        "A Kubernetes container was OOMKilled. "
        "Explain the likely cause and give a safe "
        "GitOps-based recommendation."
    )

    rag_context = build_rag_context(
        knowledge_base,
        query=query,
        top_k=2,
    )

    print(
        f"rag_context_used = "
        f"{not rag_context.empty}"
    )

    print(
        f"rag_sources = "
        f"{rag_context.sources}"
    )

    prompt = build_llm_prompt(
        query=query,
        rag_context=rag_context,
        signal_type="sre_incident",
        namespace="default",
        workload_name="checkoutservice",
    )

    bedrock_client = BedrockLLMClient(
        model_id=MODEL_ID,
        region=REGION,
        max_tokens=128,
        temperature=0.1,
    )

    request = bedrock_client.build_request(
        prompt,
        dry_run=False,
    )

    print(
        f"request.dry_run = "
        f"{request.dry_run}"
    )

    gateway = validate_bedrock_execution(
        prompt=prompt,
        request=request,
        live_authorized=live_authorized,
    )

    print(
        f"gateway.allowed = "
        f"{gateway.allowed}"
    )

    print(
        f"gateway.ready_to_invoke = "
        f"{gateway.ready_to_invoke}"
    )

    print(
        f"gateway.external_request_allowed = "
        f"{gateway.external_request_allowed}"
    )

    adapter = create_bedrock_runtime_adapter(
        config=BedrockAWSClientConfig(
            region=REGION,
        )
    )

    result = adapter.invoke(
        prompt=prompt,
        request=request,
        gateway=gateway,
    )

    print()
    print("=== BEDROCK RESPONSE ===")
    print(result.response.content)

    print()
    print("=== USAGE ===")
    print(
        f"input_tokens = "
        f"{result.input_tokens}"
    )
    print(
        f"output_tokens = "
        f"{result.output_tokens}"
    )
    print(
        f"stop_reason = "
        f"{result.stop_reason}"
    )

    print()
    print("=== SAFETY ===")
    print(
        f"runtime_invoked = "
        f"{result.runtime_invoked}"
    )
    print(
        f"external_request_performed = "
        f"{result.external_request_performed}"
    )
    print(
        f"requires_human_approval = "
        f"{result.response.requires_human_approval}"
    )
    print(
        f"allows_direct_cluster_write = "
        f"{result.response.allows_direct_cluster_write}"
    )
    print(
        f"performs_write = "
        f"{result.performs_write}"
    )


if __name__ == "__main__":
    main()
from types import SimpleNamespace

from fabcopilot.infrastructure.agent_models import OpenAIResponsesAgentModel


def test_openai_adapter_parses_function_call_with_call_id() -> None:
    response = SimpleNamespace(
        id="response-1",
        output_text="",
        output=[
            SimpleNamespace(
                type="function_call",
                call_id="call-1",
                name="query_analytics",
                arguments='{"question": "average yield"}',
            )
        ],
    )

    parsed = OpenAIResponsesAgentModel._parse_response(response)

    assert parsed.response_id == "response-1"
    assert parsed.text is None
    assert parsed.tool_calls[0].call_id == "call-1"
    assert parsed.tool_calls[0].arguments == {"question": "average yield"}

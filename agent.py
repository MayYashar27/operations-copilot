import json
from typing import Any, Callable, Dict

from anthropic import Anthropic
from dotenv import load_dotenv

from tools import (
    calculate_shift_metrics,
    count_requests_by_category,
    find_slow_requests,
)

load_dotenv()

client = Anthropic()

MODEL_NAME = "claude-sonnet-4-6"
MAX_STEPS = 5

SYSTEM_PROMPT = """
You are an AI Operations Assistant.

Your responsibility is to answer operational questions by using the available tools.

Rules:

1. Use the minimum number of tool calls required.
2. Do not call another tool if the answer can already be derived from previous tool results.
3. Base every factual statement only on tool outputs.
4. Never invent information.
5. If information is missing, clearly say so.
6. Separate facts from recommendations.
7. Do not infer causes unless they are directly supported by the data.
8. Prefer reasoning over additional tool calls when sufficient information already exists.
"""

TOOLS = [
    {
        "name": "calculate_shift_metrics",
        "description": (
            "Calculate operational metrics for a specific shift. "
            "Use when the user asks about request volume, average wait time, "
            "resolved requests or unresolved requests."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "shift": {
                    "type": "string",
                    "description": "Shift name (morning/evening).",
                }
            },
            "required": ["shift"],
            "additionalProperties": False,
        },
    },
    {
        "name": "count_requests_by_category",
        "description": (
            "Count service requests by category. "
            "Use when the user asks for category distribution."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "find_slow_requests",
        "description": (
            "Find requests whose wait time is above a threshold."
            " Optionally filter by shift."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "threshold": {
                    "type": "number",
                    "description": "Minimum wait time.",
                },
                "shift": {
                    "type": "string",
                    "description": "Optional shift.",
                },
            },
            "required": ["threshold"],
            "additionalProperties": False,
        },
    },
]

TOOL_REGISTRY: Dict[str, Callable[..., Any]] = {
    "calculate_shift_metrics": calculate_shift_metrics,
    "count_requests_by_category": count_requests_by_category,
    "find_slow_requests": find_slow_requests,
}


def extract_text(response: Any) -> str:
    text_blocks = [
        block.text
        for block in response.content
        if block.type == "text"
    ]

    return "\n".join(text_blocks).strip()


def execute_tool(tool_name: str, tool_input: Dict[str, Any]) -> Any:
    tool_function = TOOL_REGISTRY.get(tool_name)

    if tool_function is None:
        raise ValueError(f"Unknown tool requested: {tool_name}")

    return tool_function(**tool_input)


def run_agent(question: str) -> str:

    messages = [
        {
            "role": "user",
            "content": question,
        }
    ]

    for step in range(1, MAX_STEPS + 1):

        print("\n" + "=" * 60)
        print(f"AGENT STEP {step}")
        print("=" * 60)

        response = client.messages.create(
            model=MODEL_NAME,
            system=SYSTEM_PROMPT,
            max_tokens=600,
            tools=TOOLS,
            messages=messages,
        )

        tool_calls = [
            block
            for block in response.content
            if block.type == "tool_use"
        ]

        if not tool_calls:

            final_answer = extract_text(response)

            if not final_answer:
                return "Claude finished without returning an answer."

            return final_answer

        messages.append(
            {
                "role": "assistant",
                "content": response.content,
            }
        )

        tool_results = []
        for tool_call in tool_calls:

            print(f"\nClaude requested tool: {tool_call.name}")
            print(f"Arguments: {tool_call.input}")

            try:

                result = execute_tool(
                    tool_name=tool_call.name,
                    tool_input=tool_call.input,
                )

                print("\nTool Result:")
                print(result)

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": json.dumps(
                            result,
                            ensure_ascii=False,
                        ),
                    }
                )

            except Exception as exc:

                print(f"\nTool failed: {exc}")

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": str(exc),
                        "is_error": True,
                    }
                )

        messages.append(
            {
                "role": "user",
                "content": tool_results,
            }
        )

    return (
        f"The agent stopped after {MAX_STEPS} steps "
        "without producing a final answer."
    )


if __name__ == "__main__":

    question = input("\nAsk the Operations Agent a question:\n> ")

    try:

        answer = run_agent(question)

        print("\n" + "=" * 60)
        print("FINAL ANSWER")
        print("=" * 60)

        print(answer)

    except Exception as exc:

        print("\n" + "=" * 60)
        print("AGENT FAILED")
        print("=" * 60)

        print(exc)
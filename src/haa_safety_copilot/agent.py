"""Weather research agent: a tool-use loop written by hand."""

import json
from dataclasses import dataclass, field

from haa_safety_copilot.aviation_weather import WeatherAPIError
from haa_safety_copilot.llm_client import LLMClient
from haa_safety_copilot.tools import TOOLS, Tool

SYSTEM = (
    "You are the weather research step of a helicopter air ambulance pre-flight "
    "briefing tool. Use the tools to look up weather; never state weather from "
    "memory. Take every decoded value you state (wind, visibility, ceiling, "
    "clouds, temperature, dewpoint, altimeter, observation age, report flags) "
    "from the tool's fields, not from reading the raw text yourself. Quote the "
    "raw report as evidence. If something appears only in the raw text, such as "
    "remarks the tool does not decode, say it is in the raw report without "
    "interpreting it. When visibility_or_more is true, say 'or more'. If a "
    "station has no data, say so plainly. Describe conditions only: never "
    "recommend going or not going. The pilot in command makes that decision."
)


@dataclass
class AgentResult:
    answer: str
    steps: int
    stop_reason: str  # "end_turn", "max_steps", or another API stop reason
    messages: list = field(default_factory=list)


def _error_result(tool_use_id: str, message: str) -> dict:
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": message,
        "is_error": True,
    }


def _run_tool(block, tools: dict[str, Tool]) -> dict:
    tool = tools.get(block.name)
    if tool is None:
        available = ", ".join(tools)
        return _error_result(
            block.id, f"Unknown tool '{block.name}'. Available tools: {available}."
        )
    try:
        output = tool.run(**block.input)
    except TypeError as err:  # missing or unexpected arguments
        return _error_result(block.id, f"Invalid arguments for {block.name}: {err}")
    except (ValueError, WeatherAPIError) as err:
        return _error_result(block.id, f"{type(err).__name__}: {err}")
    return {
        "type": "tool_result",
        "tool_use_id": block.id,
        "content": json.dumps(output),
    }


def run_agent(
    question: str,
    client: LLMClient,
    tools: dict[str, Tool] = TOOLS,
    max_steps: int = 5,
) -> AgentResult:
    messages: list = [{"role": "user", "content": question}]
    definitions = [tool.definition for tool in tools.values()]

    for step in range(1, max_steps + 1):
        response, summary = client.chat(messages, system=SYSTEM, tools=definitions)
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            return AgentResult(summary.text, step, response.stop_reason, messages)

        results = [
            _run_tool(block, tools)
            for block in response.content
            if block.type == "tool_use"
        ]
        messages.append({"role": "user", "content": results})

    return AgentResult(
        "Stopped at the step limit before reaching an answer.",
        max_steps,
        "max_steps",
        messages,
    )

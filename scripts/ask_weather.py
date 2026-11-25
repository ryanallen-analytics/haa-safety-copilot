"""Run the weather agent on one question and print every step."""

import sys

from dotenv import load_dotenv

load_dotenv()

from haa_safety_copilot.agent import run_agent  # noqa: E402
from haa_safety_copilot.llm_client import LLMClient  # noqa: E402


def field(block, name):
    return block[name] if isinstance(block, dict) else getattr(block, name)


def main() -> None:
    question = " ".join(sys.argv[1:]) or "What are conditions at Phoenix right now?"
    result = run_agent(question, LLMClient())

    for message in result.messages:
        if isinstance(message["content"], str):
            print(f"\nUSER: {message['content']}")
            continue
        for block in message["content"]:
            kind = field(block, "type")
            if kind == "thinking":
                print("\n[thinking]")
            elif kind == "text":
                print(f"\nCLAUDE: {field(block, 'text')}")
            elif kind == "tool_use":
                print(f"\nTOOL CALL: {field(block, 'name')}({field(block, 'input')})")
            elif kind == "tool_result":
                flag = " (ERROR)" if block.get("is_error") else ""
                print(f"\nTOOL RESULT{flag}: {block['content'][:400]}")

    print(f"\n--- {result.stop_reason} after {result.steps} step(s)")


if __name__ == "__main__":
    main()

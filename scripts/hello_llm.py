"""Send one message through LLMClient and print the reply and usage."""

from dotenv import load_dotenv

from haa_safety_copilot.llm_client import LLMClient

PROMPT = (
    "In two sentences, what is a pre-flight risk analysis "
    "for a helicopter air ambulance flight?"
)


def main() -> None:
    load_dotenv()
    result = LLMClient().complete(PROMPT)
    print(result.text)
    print(
        f"\n{result.model} | in={result.input_tokens} out={result.output_tokens} | "
        f"{result.stop_reason} | {result.latency_s}s | ${result.cost_usd:.6f}"
    )


if __name__ == "__main__":
    main()

"""Send one message to the LLM and print the reply and token counts."""

import os

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()  # loads ANTHROPIC_API_KEY from .env

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-5-5")
PROMPT = (
    "In two sentences, what is a pre-flight risk analysis "
    "for a helicopter air ambulance flight?"
)


def main() -> None:
    client = Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": PROMPT}],
    )
    print(response.content[0].text)
    print(f"\nModel: {response.model}")
    print(f"Input tokens:  {response.usage.input_tokens}")
    print(f"Output tokens: {response.usage.output_tokens}")


if __name__ == "__main__":
    main()

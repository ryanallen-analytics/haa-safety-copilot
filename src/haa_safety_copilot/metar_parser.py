"""Turn a raw METAR into a validated WeatherSummary using the LLM."""

import json
from datetime import date

from pydantic import ValidationError

from haa_safety_copilot.llm_client import LLMClient
from haa_safety_copilot.weather import WeatherSummary

SYSTEM = (
    "You convert raw METAR reports into JSON. "
    "Reply with a single JSON object only: no prose, no code fences."
)


class MetarParseError(Exception):
    """The LLM did not produce a valid WeatherSummary within the allowed attempts."""


def _build_prompt(metar: str, reference_date: date) -> str:
    schema = json.dumps(WeatherSummary.model_json_schema(), indent=2)
    return (
        "Convert this METAR into JSON that matches the schema below.\n"
        f"The report is from {reference_date:%B %Y} (UTC); "
        "use that month and year for observed_at.\n"
        "Write hazards as short plain-English phrases, e.g. 'light snow', 'mist'.\n\n"
        f"METAR: {metar}\n\n"
        f"JSON schema:\n{schema}"
    )


def _strip_code_fences(text: str) -> str:
    """Remove ```json fences if the model adds them anyway."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
    return text.strip()


def parse_metar(
    metar: str,
    client: LLMClient,
    reference_date: date,
    max_attempts: int = 2,
) -> WeatherSummary:
    """Ask the LLM for a WeatherSummary; on invalid output, retry with the errors."""
    base_prompt = _build_prompt(metar, reference_date)
    prompt = base_prompt
    last_error: ValidationError | None = None

    for _ in range(max_attempts):
        response = client.complete(prompt, system=SYSTEM, max_tokens=2000)
        try:
            return WeatherSummary.model_validate_json(_strip_code_fences(response.text))
        except ValidationError as err:
            last_error = err
            prompt = (
                f"{base_prompt}\n\n"
                f"Your previous reply was:\n{response.text}\n\n"
                f"It failed validation with these errors:\n{err}\n\n"
                "Return corrected JSON only."
            )

    raise MetarParseError(
        f"No valid output after {max_attempts} attempts: {last_error}"
    )

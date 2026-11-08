"""Parse sample METARs into WeatherSummary objects with the real LLM."""

from datetime import date

from dotenv import load_dotenv

load_dotenv()

from haa_safety_copilot.llm_client import LLMClient  # noqa: E402
from haa_safety_copilot.metar_parser import parse_metar  # noqa: E402

SAMPLES = [
    "KPHX 071851Z 27008KT 10SM FEW250 29/M02 A2990",
    "KFLG 071856Z 23018G27KT 3SM -SN BR BKN008 OVC015 M02/M04 A2992",
    "KPRC 071853Z VRB04KT 1 1/2SM BR OVC004 08/07 A3001",
]


def main() -> None:
    client = LLMClient()
    for metar in SAMPLES:
        summary = parse_metar(metar, client, reference_date=date(2026, 11, 7))
        print(f"\n{metar}\n{summary.model_dump_json(indent=2)}")


if __name__ == "__main__":
    main()

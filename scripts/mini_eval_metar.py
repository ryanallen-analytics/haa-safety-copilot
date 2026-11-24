"""Mini eval: LLM-parsed METARs vs the weather API's decoded fields."""

import json
import math
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from haa_safety_copilot.aviation_weather import MetarReport, get_metar  # noqa: E402
from haa_safety_copilot.flight_conditions import assess  # noqa: E402
from haa_safety_copilot.llm_client import LLMClient  # noqa: E402
from haa_safety_copilot.metar_parser import MetarParseError, parse_metar  # noqa: E402

STATIONS = [
    "KSEA", "KPDX", "KSFO", "KDEN", "KMSP",
    "KORD", "KBOS", "KBTV", "KFLG", "PANC",
]  # fmt: skip
SNAPSHOT = Path("evals/metar_snapshot.json")
REPORT = Path("reports/mini_eval_metar.md")
FIELDS = [
    "station", "observed_at", "wind_dir", "wind_speed",
    "wind_gust", "visibility", "ceiling",
]  # fmt: skip


def load_reports() -> list[MetarReport]:
    """Reuse the saved snapshot so every rerun grades the same METARs."""
    if not SNAPSHOT.exists():
        reports = get_metar(STATIONS)
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        data = [r.model_dump(mode="json", by_alias=True) for r in reports]
        SNAPSHOT.write_text(json.dumps(data, indent=2), encoding="utf-8")
    data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    return [MetarReport.model_validate(item) for item in data]


def expected_fields(report: MetarReport, calm: bool) -> dict:
    """The answer key: API decoded fields plus the tested flight_conditions code."""
    conditions = assess(report)
    return {
        "station": report.icao_id,
        "observed_at": report.obs_time,
        "wind_dir": None if calm or report.wind_dir == "VRB" else report.wind_dir,
        "wind_speed": report.wind_speed_kt,
        "wind_gust": report.wind_gust_kt,
        "visibility": conditions.visibility.statute_miles
        if conditions.visibility
        else None,
        "ceiling": conditions.ceiling_ft,
    }


def llm_fields(summary, calm: bool) -> dict:
    return {
        "station": summary.station,
        "observed_at": summary.observed_at,
        "wind_dir": None if calm else summary.wind.direction_deg,
        "wind_speed": summary.wind.speed_kt,
        "wind_gust": summary.wind.gust_kt,
        "visibility": summary.visibility_sm,
        "ceiling": summary.ceiling_ft_agl,
    }


def same(expected, got) -> bool:
    if isinstance(expected, float) or isinstance(got, float):
        return (
            expected is not None
            and got is not None
            and math.isclose(expected, got, abs_tol=0.01)
        )
    return expected == got


def main() -> None:
    reports = load_reports()
    client = LLMClient()
    correct = dict.fromkeys(FIELDS, 0)
    mismatches: list[tuple] = []
    failures: list[str] = []

    for report in reports:
        calm = report.wind_speed_kt == 0  # direction is meaningless in calm wind
        expected = expected_fields(report, calm)
        try:
            summary = parse_metar(
                report.raw, client, reference_date=report.obs_time.date()
            )
        except MetarParseError:
            failures.append(report.raw)
            continue
        got = llm_fields(summary, calm)
        for field in FIELDS:
            if same(expected[field], got[field]):
                correct[field] += 1
            else:
                mismatches.append((report.raw, field, expected[field], got[field]))

    n = len(reports)
    lines = [
        "# Mini eval: LLM METAR parsing vs API decoded fields",
        "",
        f"{n} METARs from `{SNAPSHOT}`. Model: `{client.model}`. "
        f"Parse failures: {len(failures)}.",
        "",
        "| Field | Correct |",
        "| --- | --- |",
        *[f"| {field} | {correct[field]}/{n} |" for field in FIELDS],
        "",
        "## Mismatches",
        "",
    ]
    if mismatches:
        lines += [
            "| METAR | Field | API (expected) | LLM |",
            "| --- | --- | --- | --- |",
        ]
        lines += [
            f"| `{raw}` | {f} | {exp} | {got} |" for raw, f, exp, got in mismatches
        ]
    else:
        lines.append("None.")
    if failures:
        lines += ["", "## Parse failures", "", *[f"- `{raw}`" for raw in failures]]

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

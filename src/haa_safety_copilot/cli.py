"""Command-line interface: `haa weather KPHX`."""

from typing import Annotated

import typer

from haa_safety_copilot.aviation_weather import (
    Conditions,
    MetarReport,
    TafPeriod,
    WeatherAPIError,
    get_metar,
    get_taf,
)
from haa_safety_copilot.flight_conditions import FlightConditions, assess

DISCLAIMER = (
    "Non-operational demo. Flight categories describe conditions; "
    "the pilot in command makes every go/no-go decision."
)

app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    """HAA Safety Copilot command-line tools."""


def describe_conditions(conditions: FlightConditions) -> str:
    ceiling = (
        f"{conditions.ceiling_ft:,} ft" if conditions.ceiling_ft is not None else "none"
    )
    vis = conditions.visibility
    if vis is None:
        visibility = "missing"
    else:
        visibility = f"{vis.statute_miles:g} SM" + (" or more" if vis.at_least else "")
    parts = [
        conditions.flight_category or "UNKNOWN",
        f"ceiling {ceiling}",
        f"visibility {visibility}",
    ]
    if conditions.reported_weather:
        parts.append("weather " + " ".join(conditions.reported_weather))
    return " | ".join(parts)


def describe_wind(c: Conditions) -> str:
    if c.wind_speed_kt is None:
        return "wind missing"
    if c.wind_speed_kt == 0:
        return "wind calm"
    direction = f"{c.wind_dir:03d}" if isinstance(c.wind_dir, int) else c.wind_dir
    gust = f" gusting {c.wind_gust_kt} kt" if c.wind_gust_kt else ""
    return f"wind {direction or 'direction missing'} at {c.wind_speed_kt} kt{gust}"


def period_label(period: TafPeriod) -> str:
    if period.change is None:
        return "BASE"
    if period.change == "PROB" and period.probability:
        return f"PROB{period.probability}"
    return period.change


def print_metar(report: MetarReport) -> None:
    typer.echo(f"  {report.raw}")
    typer.echo(f"  observed {report.obs_time:%Y-%m-%d %H:%MZ}")
    typer.echo(f"  {describe_conditions(assess(report))}")
    typer.echo(f"  {describe_wind(report)}")


@app.command()
def weather(
    stations: Annotated[list[str], typer.Argument(help="ICAO codes, e.g. KPHX KFLG")],
    taf: Annotated[bool, typer.Option("--taf/--no-taf", help="Include TAFs.")] = True,
) -> None:
    """Current METAR, flight conditions, and TAF for one or more stations."""
    try:
        metars = {r.icao_id: r for r in get_metar(stations)}
        tafs = {t.icao_id: t for t in get_taf(stations)} if taf else {}
    except ValueError as err:
        typer.echo(f"Error: {err}", err=True)
        raise typer.Exit(code=2) from err
    except WeatherAPIError as err:
        typer.echo(f"Weather data unavailable: {err}", err=True)
        raise typer.Exit(code=1) from err

    for station in (s.strip().upper() for s in stations):
        typer.echo(f"\n{station}")
        if station in metars:
            print_metar(metars[station])
        else:
            typer.echo("  no METAR available")
        if not taf:
            continue
        if station in tafs:
            typer.echo(f"  {tafs[station].raw}")
            for p in tafs[station].periods:
                window = f"{p.time_from:%d %H%MZ}-{p.time_to:%d %H%MZ}"
                typer.echo(
                    f"    {period_label(p):<6} {window}"
                    f"  {describe_conditions(assess(p))} | {describe_wind(p)}"
                )
        else:
            typer.echo("  no TAF available")

    typer.echo(f"\n{DISCLAIMER}")

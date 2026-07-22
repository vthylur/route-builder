from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import typer

from route_builder.exporters import write_gpx, write_kml
from route_builder.models import RoutedDay
from route_builder.parsers import parse_input
from route_builder.routing import make_router

app = typer.Typer(no_args_is_help=True, help="Generate GPX/KML/KMZ route packages.")


@app.command()
def build(
    input_file: Path = typer.Argument(..., exists=True, dir_okay=False),
    engine: str = typer.Option("direct", help="direct, osrm or graphhopper"),
    output: Path = typer.Option(Path("output")),
    base_url: str | None = typer.Option(None, help="Custom OSRM-compatible base URL"),
    continue_on_error: bool = typer.Option(False, help="Continue and report failed days"),
) -> None:
    days = parse_input(input_file)
    if not days:
        raise typer.BadParameter("No route days found in the input")
    try:
        router = make_router(engine.lower(), base_url)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    async def run() -> None:
        output.mkdir(parents=True, exist_ok=True)
        routed: list[RoutedDay] = []
        failures: list[dict[str, object]] = []
        for day in days:
            typer.echo(f"Routing {day.route_id} day {day.day}: {day.name}")
            try:
                routed.append(await router.route(day))
            except Exception as exc:
                failures.append(
                    {"route_id": day.route_id, "day": day.day, "name": day.name, "error": str(exc)}
                )
                if not continue_on_error:
                    break

        grouped: dict[str, list[RoutedDay]] = defaultdict(list)
        for day in routed:
            grouped[day.route_id].append(day)

        for route_id, route_days in grouped.items():
            route_dir = output / route_id
            daily_dir = route_dir / "daily"
            daily_dir.mkdir(parents=True, exist_ok=True)
            for day in route_days:
                write_gpx([day], daily_dir / f"{day.name}.gpx")
            write_gpx(route_days, route_dir / f"{route_id}_master.gpx")
            kml_path = route_dir / f"{route_id}.kml"
            write_kml(route_days, kml_path)
            with ZipFile(route_dir / f"{route_id}.kmz", "w", ZIP_DEFLATED) as archive:
                archive.write(kml_path, arcname="doc.kml")

        report = {
            "engine": engine,
            "input": str(input_file),
            "routed_days": len(routed),
            "failed_days": len(failures),
            "failures": failures,
            "warnings": [
                {"route_id": day.route_id, "day": day.day, "warnings": day.warnings}
                for day in routed
                if day.warnings
            ],
        }
        (output / "validation_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        typer.echo(f"Completed {len(routed)} day(s); failed {len(failures)} day(s).")
        if failures and not continue_on_error:
            raise typer.Exit(code=1)

    asyncio.run(run())


if __name__ == "__main__":
    app()

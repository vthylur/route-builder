from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import typer

from route_builder.diagnostics import route_manifest, validate_day
from route_builder.exporters import write_geojson, write_gpx, write_kml
from route_builder.intelligence import elevation_summary, fuel_analysis, load_vehicle_profile
from route_builder.models import RoutedDay
from route_builder.parsers import parse_input, parse_pois
from route_builder.reports import write_html_report
from route_builder.routing import make_router

app = typer.Typer(no_args_is_help=True, help="Generate and validate route packages.")


def _input_diagnostics(days) -> list[dict[str, object]]:
    diagnostics: list[dict[str, object]] = []
    for day in days:
        warnings = validate_day(day)
        if warnings:
            diagnostics.append(
                {"route_id": day.route_id, "day": day.day, "name": day.name, "warnings": warnings}
            )
    return diagnostics


@app.command("validate")
def validate_input(
    input_file: Path = typer.Argument(..., exists=True, dir_okay=False),
    report: Path | None = typer.Option(None, help="Optional JSON report path"),
    strict: bool = typer.Option(False, help="Exit with code 1 when warnings are found"),
) -> None:
    """Validate itinerary structure without calling a routing service."""
    days = parse_input(input_file)
    pois = parse_pois(input_file)
    warnings = _input_diagnostics(days)
    route_ids = sorted({day.route_id for day in days})
    payload = {
        "schema_version": "1.0",
        "input": str(input_file),
        "route_count": len(route_ids),
        "day_count": len(days),
        "waypoint_count": sum(len(day.waypoints) for day in days),
        "poi_count": len(pois),
        "warnings": warnings,
    }
    if report:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    typer.echo(json.dumps(payload, indent=2))
    if strict and warnings:
        raise typer.Exit(code=1)


@app.command()
def build(
    input_file: Path = typer.Argument(..., exists=True, dir_okay=False),
    engine: str = typer.Option("direct", help="direct, osrm or graphhopper"),
    output: Path = typer.Option(Path("output")),
    base_url: str | None = typer.Option(None, help="Custom OSRM-compatible base URL"),
    vehicle_profile: Path | None = typer.Option(
        None, exists=True, dir_okay=False, help="Vehicle profile JSON for fuel analysis"
    ),
    html_report: bool = typer.Option(True, help="Generate a self-contained expedition report"),
    continue_on_error: bool = typer.Option(False, help="Continue and report failed days"),
) -> None:
    days = parse_input(input_file)
    pois = parse_pois(input_file)
    profile = load_vehicle_profile(vehicle_profile)
    if not days:
        raise typer.BadParameter("No route days found in the input")
    try:
        router = make_router(engine.lower(), base_url)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    input_warnings = _input_diagnostics(days)
    source_days = {(day.route_id, day.day): day for day in days}

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

        manifests: list[dict[str, object]] = []
        for route_id, route_days in grouped.items():
            route_pois = [poi for poi in pois if poi.route_id == route_id]
            route_dir = output / route_id
            daily_dir = route_dir / "daily"
            daily_dir.mkdir(parents=True, exist_ok=True)
            for day in route_days:
                day_pois = [poi for poi in route_pois if poi.day in (None, day.day)]
                write_gpx([day], daily_dir / f"{day.name}.gpx", day_pois)
                write_geojson([day], daily_dir / f"{day.name}.geojson", day_pois)
            write_gpx(route_days, route_dir / f"{route_id}_master.gpx", route_pois)
            write_geojson(route_days, route_dir / f"{route_id}.geojson", route_pois)
            kml_path = route_dir / f"{route_id}.kml"
            write_kml(route_days, kml_path, route_pois)
            with ZipFile(route_dir / f"{route_id}.kmz", "w", ZIP_DEFLATED) as archive:
                archive.write(kml_path, arcname="doc.kml")

            manifest = route_manifest(route_id, route_days, route_pois)
            for day_entry in manifest["days"]:
                key = (route_id, day_entry["day"])
                source = source_days[key]
                routed_day = next(item for item in route_days if item.day == day_entry["day"])
                day_entry["elevation"] = elevation_summary(source)
                day_entry["fuel"] = fuel_analysis(routed_day, profile, route_pois)
            manifest["vehicle_profile"] = profile.model_dump(mode="json") if profile else None
            manifests.append(manifest)
            (route_dir / "manifest.json").write_text(
                json.dumps(manifest, indent=2), encoding="utf-8"
            )
            if html_report:
                write_html_report(manifest, route_dir / "report.html")

        report = {
            "schema_version": "1.0",
            "engine": engine,
            "input": str(input_file),
            "vehicle_profile": profile.model_dump(mode="json") if profile else None,
            "routed_days": len(routed),
            "poi_count": len(pois),
            "failed_days": len(failures),
            "failures": failures,
            "input_warnings": input_warnings,
            "routing_warnings": [
                {"route_id": day.route_id, "day": day.day, "warnings": day.warnings}
                for day in routed
                if day.warnings
            ],
            "routes": manifests,
        }
        (output / "validation_report.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        typer.echo(
            f"Completed {len(routed)} day(s), {len(pois)} POI(s); "
            f"failed {len(failures)} day(s), input warnings {len(input_warnings)}."
        )
        if failures and not continue_on_error:
            raise typer.Exit(code=1)

    asyncio.run(run())


if __name__ == "__main__":
    app()

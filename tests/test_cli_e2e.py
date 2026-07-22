from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

from typer.testing import CliRunner

from route_builder.cli import app

runner = CliRunner()


def _write_itinerary(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "waypoints": [
                    {
                        "route_id": "R01",
                        "day": 1,
                        "sequence": 1,
                        "name": "Start",
                        "latitude": 12.0,
                        "longitude": 77.0,
                        "elevation_m": 900,
                        "segment_mode": "off-road",
                    },
                    {
                        "route_id": "R01",
                        "day": 1,
                        "sequence": 2,
                        "name": "Finish",
                        "latitude": 12.1,
                        "longitude": 77.1,
                        "elevation_m": 1200,
                    },
                ],
                "pois": [
                    {
                        "route_id": "R01",
                        "type": "fuel",
                        "name": "Fuel Stop",
                        "latitude": 12.05,
                        "longitude": 77.05,
                        "day": 1,
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_validate_command_writes_machine_readable_report(tmp_path: Path) -> None:
    source = tmp_path / "route.json"
    report = tmp_path / "validation.json"
    _write_itinerary(source)

    result = runner.invoke(app, ["validate", str(source), "--report", str(report)])

    assert result.exit_code == 0, result.output
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["route_count"] == 1
    assert payload["day_count"] == 1
    assert payload["waypoint_count"] == 2
    assert payload["poi_count"] == 1


def test_build_command_produces_complete_route_package(tmp_path: Path) -> None:
    source = tmp_path / "route.json"
    output = tmp_path / "output"
    _write_itinerary(source)

    result = runner.invoke(
        app,
        ["build", str(source), "--engine", "direct", "--output", str(output)],
    )

    assert result.exit_code == 0, result.output
    route_dir = output / "R01"
    expected = {
        "R01_master.gpx",
        "R01.geojson",
        "R01.kml",
        "R01.kmz",
        "manifest.json",
        "report.html",
    }
    assert expected.issubset({item.name for item in route_dir.iterdir()})
    assert len(list((route_dir / "daily").glob("*.gpx"))) == 1
    assert len(list((route_dir / "daily").glob("*.geojson"))) == 1

    manifest = json.loads((route_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["route_id"] == "R01"
    assert manifest["day_count"] == 1
    assert manifest["days"][0]["elevation"]["ascent_m"] == 300

    validation = json.loads((output / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["failed_days"] == 0
    assert validation["routed_days"] == 1

    with ZipFile(route_dir / "R01.kmz") as archive:
        assert archive.namelist() == ["doc.kml"]

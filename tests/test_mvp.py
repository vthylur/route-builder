from __future__ import annotations

import asyncio
import json
from pathlib import Path
from xml.etree import ElementTree

from openpyxl import Workbook

from route_builder.diagnostics import route_manifest, validate_day
from route_builder.exporters import write_geojson, write_gpx, write_kml
from route_builder.intelligence import elevation_summary, fuel_analysis
from route_builder.models import DayRoute, POI, POIType, SegmentMode, VehicleProfile, Waypoint
from route_builder.parsers import parse_csv, parse_excel, parse_pois
from route_builder.reports import write_html_report
from route_builder.routing import DirectRouter, MixedRouter


def test_parse_csv_orders_waypoints(tmp_path: Path) -> None:
    path = tmp_path / "route.csv"
    path.write_text(
        "Route ID,Day,Sequence,Name,Latitude,Longitude,Elevation m,Segment Mode\n"
        "R01,1,2,Finish,13,78,2500,route\n"
        "R01,1,1,Start,12,77,1000,off-road\n",
        encoding="utf-8",
    )
    day = parse_csv(path)[0]
    assert [point.name for point in day.waypoints] == ["Start", "Finish"]
    assert day.waypoints[0].segment_mode == SegmentMode.OFF_ROAD
    assert elevation_summary(day)["ascent_m"] == 1500


def test_parse_excel_and_pois(tmp_path: Path) -> None:
    path = tmp_path / "route.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Route Waypoints"
    sheet.append(["Route ID", "Day", "Sequence", "Name", "Latitude", "Longitude"])
    sheet.append(["R01", 1, 1, "Start", 12.0, 77.0])
    sheet.append(["R01", 1, 2, "Finish", 13.0, 78.0])
    poi_sheet = workbook.create_sheet("POIs")
    poi_sheet.append(["Route ID", "Type", "Name", "Latitude", "Longitude", "Day", "Notes"])
    poi_sheet.append(["R01", "fuel", "Fuel Stop", 12.5, 77.5, 1, "24-hour pump"])
    workbook.save(path)
    assert len(parse_excel(path)) == 1
    assert parse_pois(path)[0].poi_type == POIType.FUEL


def test_exporters_write_xml_and_geojson(tmp_path: Path) -> None:
    day = DayRoute(
        route_id="R01",
        day=1,
        name="D01_Test",
        waypoints=[
            Waypoint(route_id="R01", day=1, sequence=1, name="A", latitude=12, longitude=77),
            Waypoint(route_id="R01", day=1, sequence=2, name="B", latitude=13, longitude=78),
        ],
    )
    routed = asyncio.run(DirectRouter().route(day))
    poi = POI(route_id="R01", name="Clinic", poi_type="medical", latitude=12.2, longitude=77.2)
    gpx = tmp_path / "route.gpx"
    kml = tmp_path / "route.kml"
    geojson = tmp_path / "route.geojson"
    write_gpx([routed], gpx, [poi])
    write_kml([routed], kml, [poi])
    write_geojson([routed], geojson, [poi])
    assert ElementTree.parse(gpx).find("{http://www.topografix.com/GPX/1/1}wpt") is not None
    assert "Medical" in kml.read_text(encoding="utf-8")
    payload = json.loads(geojson.read_text(encoding="utf-8"))
    assert payload["type"] == "FeatureCollection"
    assert len(payload["features"]) == 2


def test_mixed_router_records_segment_diagnostic() -> None:
    day = DayRoute(
        route_id="R01",
        day=1,
        name="Mixed",
        waypoints=[
            Waypoint(
                route_id="R01", day=1, sequence=1, name="A", latitude=12, longitude=77,
                segment_mode=SegmentMode.OFF_ROAD,
            ),
            Waypoint(route_id="R01", day=1, sequence=2, name="B", latitude=13, longitude=78),
        ],
    )
    routed = asyncio.run(MixedRouter(DirectRouter()).route(day))
    assert routed.geometry == [(12.0, 77.0), (13.0, 78.0)]
    assert routed.segments[0].mode == SegmentMode.OFF_ROAD
    assert routed.segments[0].point_count == 2


def test_validation_and_manifest() -> None:
    day = DayRoute(
        route_id="R01",
        day=1,
        name="Duplicates",
        waypoints=[
            Waypoint(route_id="R01", day=1, sequence=1, name="A", latitude=12, longitude=77),
            Waypoint(route_id="R01", day=1, sequence=2, name="A", latitude=12, longitude=77),
        ],
    )
    warnings = validate_day(day)
    assert any("Duplicate waypoint name" in warning for warning in warnings)
    routed = asyncio.run(DirectRouter().route(day))
    manifest = route_manifest("R01", [routed], [])
    assert manifest["route_id"] == "R01"
    assert manifest["bounds"]["south"] == 12.0


def test_fuel_analysis_and_html_report(tmp_path: Path) -> None:
    day = DayRoute(
        route_id="R01",
        day=1,
        name="Long_Day",
        waypoints=[
            Waypoint(route_id="R01", day=1, sequence=1, name="A", latitude=12, longitude=77),
            Waypoint(route_id="R01", day=1, sequence=2, name="B", latitude=13, longitude=78),
        ],
    )
    routed = asyncio.run(DirectRouter().route(day)).model_copy(update={"distance_m": 300_000})
    profile = VehicleProfile(
        name="Test Bike", fuel_capacity_l=10, reserve_l=1, efficiency_kmpl=30,
        safety_margin_percent=10,
    )
    fuel = fuel_analysis(routed, profile, [])
    assert fuel["warning"]
    manifest = route_manifest("R01", [routed], [])
    manifest["days"][0]["fuel"] = fuel
    manifest["days"][0]["elevation"] = elevation_summary(day)
    report = tmp_path / "report.html"
    write_html_report(manifest, report)
    assert "Test Bike" not in report.read_text(encoding="utf-8")
    assert "Fuel warning" in report.read_text(encoding="utf-8")

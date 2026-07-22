from __future__ import annotations

import asyncio
from pathlib import Path
from xml.etree import ElementTree

from openpyxl import Workbook

from route_builder.exporters import write_gpx, write_kml
from route_builder.models import DayRoute, POI, POIType, SegmentMode, Waypoint
from route_builder.parsers import parse_csv, parse_excel, parse_pois
from route_builder.routing import DirectRouter, MixedRouter


def test_parse_csv_orders_waypoints(tmp_path: Path) -> None:
    path = tmp_path / "route.csv"
    path.write_text(
        "Route ID,Day,Sequence,Name,Latitude,Longitude,Segment Mode\n"
        "R01,1,2,Finish,13,78,route\n"
        "R01,1,1,Start,12,77,off-road\n",
        encoding="utf-8",
    )
    day = parse_csv(path)[0]
    assert [point.name for point in day.waypoints] == ["Start", "Finish"]
    assert day.waypoints[0].segment_mode == SegmentMode.OFF_ROAD


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


def test_direct_router_warns_and_exporters_write_valid_xml(tmp_path: Path) -> None:
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
    assert routed.warnings
    gpx = tmp_path / "route.gpx"
    kml = tmp_path / "route.kml"
    write_gpx([routed], gpx, [poi])
    write_kml([routed], kml, [poi])
    assert ElementTree.parse(gpx).find("{http://www.topografix.com/GPX/1/1}wpt") is not None
    assert "Medical" in kml.read_text(encoding="utf-8")


def test_mixed_router_uses_direct_geometry_for_offroad_segment() -> None:
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
    assert "off-road" in routed.warnings[0]

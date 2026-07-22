from __future__ import annotations

import asyncio
from pathlib import Path
from xml.etree import ElementTree

from openpyxl import Workbook

from route_builder.exporters import write_gpx, write_kml
from route_builder.models import DayRoute, RoutedDay, Waypoint
from route_builder.parsers import parse_csv, parse_excel
from route_builder.routing import DirectRouter


def test_parse_csv_orders_waypoints(tmp_path: Path) -> None:
    path = tmp_path / "route.csv"
    path.write_text(
        "Route ID,Day,Sequence,Name,Latitude,Longitude,Segment Mode\n"
        "R01,1,2,Finish,13,78,route\n"
        "R01,1,1,Start,12,77,route\n",
        encoding="utf-8",
    )
    day = parse_csv(path)[0]
    assert [point.name for point in day.waypoints] == ["Start", "Finish"]


def test_parse_excel(tmp_path: Path) -> None:
    path = tmp_path / "route.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Route Waypoints"
    sheet.append(["Route ID", "Day", "Sequence", "Name", "Latitude", "Longitude"])
    sheet.append(["R01", 1, 1, "Start", 12.0, 77.0])
    sheet.append(["R01", 1, 2, "Finish", 13.0, 78.0])
    workbook.save(path)
    assert len(parse_excel(path)) == 1


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
    assert routed.warnings
    gpx = tmp_path / "route.gpx"
    kml = tmp_path / "route.kml"
    write_gpx([routed], gpx)
    write_kml([routed], kml)
    ElementTree.parse(gpx)
    ElementTree.parse(kml)

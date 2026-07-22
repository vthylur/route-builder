from __future__ import annotations

import json
from pathlib import Path
from xml.etree.ElementTree import Element, ElementTree, SubElement

from route_builder.models import POI, RoutedDay

COLOURS = [
    "ff0000ff", "ff00a5ff", "ff00ff00", "ffff0000", "ffff00ff",
    "ff00ffff", "ff8b008b", "ff2a2aa5", "ffffff00", "ff008000",
]


def _add_gpx_track(root: Element, day: RoutedDay) -> None:
    track = SubElement(root, "trk")
    SubElement(track, "name").text = day.name
    if day.warnings:
        SubElement(track, "desc").text = " | ".join(day.warnings)
    segment = SubElement(track, "trkseg")
    for latitude, longitude in day.geometry:
        SubElement(segment, "trkpt", {"lat": f"{latitude:.7f}", "lon": f"{longitude:.7f}"})


def write_gpx(days: list[RoutedDay], path: Path, pois: list[POI] | None = None) -> None:
    engines = ",".join(sorted({day.engine for day in days}))
    root = Element(
        "gpx",
        {
            "version": "1.1",
            "creator": f"Route Builder ({engines})",
            "xmlns": "http://www.topografix.com/GPX/1/1",
        },
    )
    metadata = SubElement(root, "metadata")
    SubElement(metadata, "name").text = path.stem
    for poi in pois or []:
        waypoint = SubElement(
            root,
            "wpt",
            {"lat": f"{poi.latitude:.7f}", "lon": f"{poi.longitude:.7f}"},
        )
        SubElement(waypoint, "name").text = poi.name
        SubElement(waypoint, "type").text = poi.poi_type.value
        if poi.notes:
            SubElement(waypoint, "desc").text = poi.notes
    for day in sorted(days, key=lambda item: item.day):
        _add_gpx_track(root, day)
    ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def write_kml(days: list[RoutedDay], path: Path, pois: list[POI] | None = None) -> None:
    kml = Element("kml", {"xmlns": "http://www.opengis.net/kml/2.2"})
    document = SubElement(kml, "Document")
    SubElement(document, "name").text = path.stem
    for index, day in enumerate(sorted(days, key=lambda item: item.day)):
        style_id = f"day-{day.day}"
        style = SubElement(document, "Style", {"id": style_id})
        line_style = SubElement(style, "LineStyle")
        SubElement(line_style, "color").text = COLOURS[index % len(COLOURS)]
        SubElement(line_style, "width").text = "5"
        folder = SubElement(document, "Folder")
        SubElement(folder, "name").text = f"Day {day.day}: {day.name}"
        placemark = SubElement(folder, "Placemark")
        SubElement(placemark, "name").text = day.name
        SubElement(placemark, "styleUrl").text = f"#{style_id}"
        description = [f"Engine: {day.engine}"]
        if day.distance_m is not None:
            description.append(f"Distance: {day.distance_m / 1000:.1f} km")
        if day.duration_s is not None:
            description.append(f"Duration: {day.duration_s / 3600:.1f} h")
        description.extend(day.warnings)
        SubElement(placemark, "description").text = " | ".join(description)
        line = SubElement(placemark, "LineString")
        SubElement(line, "tessellate").text = "1"
        SubElement(line, "coordinates").text = " ".join(
            f"{longitude:.7f},{latitude:.7f},0" for latitude, longitude in day.geometry
        )

    grouped: dict[str, list[POI]] = {}
    for poi in pois or []:
        grouped.setdefault(poi.poi_type.value, []).append(poi)
    for poi_type, items in sorted(grouped.items()):
        folder = SubElement(document, "Folder")
        SubElement(folder, "name").text = poi_type.replace("-", " ").title()
        for poi in items:
            placemark = SubElement(folder, "Placemark")
            SubElement(placemark, "name").text = poi.name
            if poi.notes:
                SubElement(placemark, "description").text = poi.notes
            point = SubElement(placemark, "Point")
            SubElement(point, "coordinates").text = f"{poi.longitude:.7f},{poi.latitude:.7f},0"

    ElementTree(kml).write(path, encoding="utf-8", xml_declaration=True)


def write_geojson(days: list[RoutedDay], path: Path, pois: list[POI] | None = None) -> None:
    features: list[dict[str, object]] = []
    for day in sorted(days, key=lambda item: item.day):
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[lon, lat] for lat, lon in day.geometry],
                },
                "properties": {
                    "route_id": day.route_id,
                    "day": day.day,
                    "name": day.name,
                    "engine": day.engine,
                    "distance_m": day.distance_m,
                    "duration_s": day.duration_s,
                    "warnings": day.warnings,
                },
            }
        )
    for poi in pois or []:
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [poi.longitude, poi.latitude],
                },
                "properties": {
                    "route_id": poi.route_id,
                    "day": poi.day,
                    "name": poi.name,
                    "type": poi.poi_type.value,
                    "notes": poi.notes,
                },
            }
        )
    path.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, indent=2),
        encoding="utf-8",
    )

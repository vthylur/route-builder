from __future__ import annotations

from pathlib import Path
from xml.etree.ElementTree import Element, ElementTree, SubElement

from route_builder.models import RoutedDay

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


def write_gpx(days: list[RoutedDay], path: Path) -> None:
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
    for day in sorted(days, key=lambda item: item.day):
        _add_gpx_track(root, day)
    ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def write_kml(days: list[RoutedDay], path: Path) -> None:
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
        description.extend(day.warnings)
        SubElement(placemark, "description").text = " | ".join(description)
        line = SubElement(placemark, "LineString")
        SubElement(line, "tessellate").text = "1"
        SubElement(line, "coordinates").text = " ".join(
            f"{longitude:.7f},{latitude:.7f},0" for latitude, longitude in day.geometry
        )
    ElementTree(kml).write(path, encoding="utf-8", xml_declaration=True)

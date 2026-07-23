from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

from route_builder.models import DayRoute, POI, RoutedDay


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = map(radians, a)
    lat2, lon2 = map(radians, b)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    value = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * 6_371_000 * asin(sqrt(value))


def validate_day(day: DayRoute) -> list[str]:
    warnings: list[str] = []
    seen_names: set[str] = set()
    seen_coordinates: set[tuple[float, float]] = set()
    for point in day.waypoints:
        normalized = point.name.casefold().strip()
        coordinate = (round(point.latitude, 6), round(point.longitude, 6))
        if normalized in seen_names:
            warnings.append(f"Duplicate waypoint name: {point.name}")
        if coordinate in seen_coordinates:
            warnings.append(f"Duplicate waypoint coordinate: {point.name}")
        seen_names.add(normalized)
        seen_coordinates.add(coordinate)

    for start, end in zip(day.waypoints, day.waypoints[1:], strict=False):
        separation = haversine_m(
            (start.latitude, start.longitude), (end.latitude, end.longitude)
        )
        if separation < 10:
            warnings.append(f"Near-zero segment: {start.name} → {end.name} ({separation:.1f} m)")
        if separation > 500_000:
            warnings.append(
                f"Very long waypoint gap: {start.name} → {end.name} ({separation / 1000:.1f} km)"
            )
    return warnings


def route_manifest(route_id: str, days: list[RoutedDay], pois: list[POI]) -> dict[str, object]:
    ordered = sorted(days, key=lambda item: item.day)
    coordinates = [point for day in ordered for point in day.geometry]
    total_distance = sum(day.distance_m or 0 for day in ordered)
    total_duration = sum(day.duration_s or 0 for day in ordered)
    bounds = None
    if coordinates:
        latitudes = [point[0] for point in coordinates]
        longitudes = [point[1] for point in coordinates]
        bounds = {
            "south": min(latitudes),
            "west": min(longitudes),
            "north": max(latitudes),
            "east": max(longitudes),
        }
    return {
        "schema_version": "1.0",
        "route_id": route_id,
        "day_count": len(ordered),
        "poi_count": len(pois),
        "total_distance_m": total_distance or None,
        "total_duration_s": total_duration or None,
        "bounds": bounds,
        "days": [
            {
                "day": day.day,
                "name": day.name,
                "engine": day.engine,
                "distance_m": day.distance_m,
                "duration_s": day.duration_s,
                "point_count": len(day.geometry),
                "warning_count": len(day.warnings),
                "segments": [segment.model_dump(mode="json") for segment in day.segments],
            }
            for day in ordered
        ],
        "pois": [poi.model_dump(mode="json") for poi in pois],
    }

from __future__ import annotations

import json
from pathlib import Path

from route_builder.models import DayRoute, POI, POIType, RoutedDay, VehicleProfile


def load_vehicle_profile(path: Path | None) -> VehicleProfile | None:
    if path is None:
        return None
    return VehicleProfile.model_validate(json.loads(path.read_text(encoding="utf-8")))


def elevation_summary(day: DayRoute) -> dict[str, float | None]:
    elevations = [point.elevation_m for point in day.waypoints if point.elevation_m is not None]
    if not elevations:
        return {"min_elevation_m": None, "max_elevation_m": None, "ascent_m": None, "descent_m": None}
    ascent = 0.0
    descent = 0.0
    for start, end in zip(elevations, elevations[1:], strict=False):
        delta = end - start
        if delta > 0:
            ascent += delta
        else:
            descent += abs(delta)
    return {
        "min_elevation_m": min(elevations),
        "max_elevation_m": max(elevations),
        "ascent_m": ascent,
        "descent_m": descent,
    }


def fuel_analysis(
    routed_day: RoutedDay,
    profile: VehicleProfile | None,
    pois: list[POI],
) -> dict[str, object]:
    if profile is None:
        return {"enabled": False}
    distance_km = routed_day.distance_m / 1000 if routed_day.distance_m is not None else None
    range_km = profile.usable_range_km
    fuel_stops = [poi for poi in pois if poi.poi_type == POIType.FUEL and poi.day in (None, routed_day.day)]
    warning = None
    if distance_km is None:
        warning = "Distance unavailable; fuel sufficiency cannot be calculated."
    elif distance_km > range_km:
        warning = (
            f"Planned day distance {distance_km:.1f} km exceeds usable range "
            f"{range_km:.1f} km. Add a verified fuel stop or carry approved reserve fuel."
        )
    elif distance_km > range_km * 0.8 and not fuel_stops:
        warning = (
            f"Planned day uses more than 80% of usable range ({distance_km:.1f}/{range_km:.1f} km) "
            "and no fuel POI is recorded."
        )
    return {
        "enabled": True,
        "vehicle": profile.name,
        "usable_range_km": round(range_km, 1),
        "planned_distance_km": round(distance_km, 1) if distance_km is not None else None,
        "range_utilisation_percent": round(distance_km / range_km * 100, 1)
        if distance_km is not None and range_km > 0
        else None,
        "fuel_poi_count": len(fuel_stops),
        "warning": warning,
    }

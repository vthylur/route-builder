from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import httpx

from route_builder.models import DayRoute, Waypoint


@dataclass(frozen=True)
class ElevationResult:
    provider: str
    requested: int
    populated: int
    warnings: tuple[str, ...] = ()


class OpenElevationProvider:
    name = "open-elevation"

    def __init__(self, base_url: str = "https://api.open-elevation.com") -> None:
        self.base_url = base_url.rstrip("/")

    async def lookup(self, coordinates: Sequence[tuple[float, float]]) -> list[float]:
        if not coordinates:
            return []
        payload = {
            "locations": [
                {"latitude": latitude, "longitude": longitude}
                for latitude, longitude in coordinates
            ]
        }
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(f"{self.base_url}/api/v1/lookup", json=payload)
            response.raise_for_status()
            body = response.json()
        results = body.get("results")
        if not isinstance(results, list) or len(results) != len(coordinates):
            raise RuntimeError("Elevation provider returned an unexpected result count")
        elevations: list[float] = []
        for item in results:
            if not isinstance(item, dict) or item.get("elevation") is None:
                raise RuntimeError("Elevation provider returned a result without elevation")
            elevations.append(float(item["elevation"]))
        return elevations


async def enrich_day_elevations(
    day: DayRoute,
    provider: OpenElevationProvider,
    overwrite: bool = False,
) -> tuple[DayRoute, ElevationResult]:
    indexes = [
        index
        for index, waypoint in enumerate(day.waypoints)
        if overwrite or waypoint.elevation_m is None
    ]
    coordinates = [
        (day.waypoints[index].latitude, day.waypoints[index].longitude) for index in indexes
    ]
    elevations = await provider.lookup(coordinates)
    updated = list(day.waypoints)
    for index, elevation in zip(indexes, elevations, strict=True):
        updated[index] = updated[index].model_copy(update={"elevation_m": elevation})
    return (
        day.model_copy(update={"waypoints": updated}),
        ElevationResult(provider=provider.name, requested=len(indexes), populated=len(elevations)),
    )


def make_elevation_provider(engine: str | None, base_url: str | None = None):
    normalized = (engine or "none").strip().lower()
    if normalized in {"none", "off", "disabled"}:
        return None
    if normalized == "open-elevation":
        return OpenElevationProvider(base_url or "https://api.open-elevation.com")
    raise ValueError("elevation engine must be none or open-elevation")

from __future__ import annotations

import os
import httpx

from route_builder.models import DayRoute, RoutedDay


class DirectRouter:
    name = "direct"

    async def route(self, day: DayRoute) -> RoutedDay:
        return RoutedDay(
            route_id=day.route_id,
            day=day.day,
            name=day.name,
            geometry=[(p.latitude, p.longitude) for p in day.waypoints],
            engine=self.name,
            warnings=["Direct reference geometry; this track is not road-routed."],
        )


class OSRMRouter:
    name = "osrm"

    def __init__(self, base_url: str = "https://router.project-osrm.org") -> None:
        self.base_url = base_url.rstrip("/")

    async def route(self, day: DayRoute) -> RoutedDay:
        coordinates = ";".join(f"{p.longitude},{p.latitude}" for p in day.waypoints)
        url = f"{self.base_url}/route/v1/driving/{coordinates}"
        params = {"overview": "full", "geometries": "geojson", "steps": "false"}
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
        if payload.get("code") != "Ok" or not payload.get("routes"):
            raise RuntimeError(f"OSRM could not route {day.name}: {payload.get('message', payload)}")
        route = payload["routes"][0]
        return RoutedDay(
            route_id=day.route_id,
            day=day.day,
            name=day.name,
            geometry=[(lat, lon) for lon, lat in route["geometry"]["coordinates"]],
            distance_m=route.get("distance"),
            duration_s=route.get("duration"),
            engine=self.name,
        )


class GraphHopperRouter:
    name = "graphhopper"

    def __init__(self, api_key: str | None = None, profile: str = "car") -> None:
        self.api_key = api_key or os.getenv("GRAPHHOPPER_API_KEY")
        self.profile = profile
        if not self.api_key:
            raise ValueError("Set GRAPHHOPPER_API_KEY")

    async def route(self, day: DayRoute) -> RoutedDay:
        params: list[tuple[str, str]] = [
            ("profile", self.profile),
            ("points_encoded", "false"),
            ("key", self.api_key),
        ]
        params.extend(("point", f"{p.latitude},{p.longitude}") for p in day.waypoints)
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.get("https://graphhopper.com/api/1/route", params=params)
            response.raise_for_status()
            payload = response.json()
        if not payload.get("paths"):
            raise RuntimeError(f"GraphHopper could not route {day.name}: {payload}")
        path = payload["paths"][0]
        return RoutedDay(
            route_id=day.route_id,
            day=day.day,
            name=day.name,
            geometry=[(lat, lon) for lon, lat in path["points"]["coordinates"]],
            distance_m=path.get("distance"),
            duration_s=path.get("time", 0) / 1000,
            engine=self.name,
        )


def make_router(engine: str, base_url: str | None = None):
    if engine == "direct":
        return DirectRouter()
    if engine == "osrm":
        return OSRMRouter(base_url or "https://router.project-osrm.org")
    if engine == "graphhopper":
        return GraphHopperRouter()
    raise ValueError("engine must be direct, osrm or graphhopper")

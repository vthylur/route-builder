from __future__ import annotations

import os
import re

import httpx

from route_builder.models import DayRoute, RoutedDay, SegmentDiagnostic, SegmentMode, Waypoint

_PROFILE_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def _validated_profile(profile: str) -> str:
    value = profile.strip()
    if not value or not _PROFILE_PATTERN.fullmatch(value):
        raise ValueError("routing profile must contain only letters, numbers, hyphens or underscores")
    return value


def _pair_day(day: DayRoute, start: Waypoint, end: Waypoint) -> DayRoute:
    return DayRoute(
        route_id=day.route_id,
        day=day.day,
        name=f"{start.name}_to_{end.name}",
        waypoints=[start, end],
    )


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

    def __init__(
        self,
        base_url: str = "https://router.project-osrm.org",
        profile: str = "driving",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.profile = _validated_profile(profile)

    async def route(self, day: DayRoute) -> RoutedDay:
        coordinates = ";".join(f"{p.longitude},{p.latitude}" for p in day.waypoints)
        url = f"{self.base_url}/route/v1/{self.profile}/{coordinates}"
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
            engine=f"{self.name}:{self.profile}",
        )


class GraphHopperRouter:
    name = "graphhopper"

    def __init__(self, api_key: str | None = None, profile: str = "car") -> None:
        self.api_key = api_key or os.getenv("GRAPHHOPPER_API_KEY")
        self.profile = _validated_profile(profile)
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
            engine=f"{self.name}:{self.profile}",
        )


class MixedRouter:
    """Route each waypoint pair according to the start waypoint's Segment Mode."""

    def __init__(self, road_router) -> None:
        self.road_router = road_router
        self.direct_router = DirectRouter()
        self.name = f"mixed:{road_router.name}"

    async def route(self, day: DayRoute) -> RoutedDay:
        if len(day.waypoints) == 1:
            return await self.direct_router.route(day)

        geometry: list[tuple[float, float]] = []
        distance_m = 0.0
        duration_s = 0.0
        has_distance = False
        has_duration = False
        warnings: list[str] = []
        diagnostics: list[SegmentDiagnostic] = []

        direct_modes = {
            SegmentMode.DIRECT,
            SegmentMode.OFF_ROAD,
            SegmentMode.WALKING,
            SegmentMode.FERRY,
            SegmentMode.UNKNOWN,
        }
        for sequence, (start, end) in enumerate(
            zip(day.waypoints, day.waypoints[1:], strict=False), start=1
        ):
            segment = _pair_day(day, start, end)
            segment_warnings: list[str] = []
            if start.segment_mode in direct_modes:
                routed = await self.direct_router.route(segment)
                segment_warnings.append(
                    f"{start.name} → {end.name}: {start.segment_mode.value} segment exported as direct geometry."
                )
            else:
                routed = await self.road_router.route(segment)
                segment_warnings.extend(routed.warnings)

            points = routed.geometry
            if geometry and points and geometry[-1] == points[0]:
                points = points[1:]
            geometry.extend(points)
            warnings.extend(segment_warnings)
            if routed.distance_m is not None:
                distance_m += routed.distance_m
                has_distance = True
            if routed.duration_s is not None:
                duration_s += routed.duration_s
                has_duration = True
            diagnostics.append(
                SegmentDiagnostic(
                    sequence=sequence,
                    start_name=start.name,
                    end_name=end.name,
                    mode=start.segment_mode,
                    engine=routed.engine,
                    point_count=len(routed.geometry),
                    distance_m=routed.distance_m,
                    duration_s=routed.duration_s,
                    warnings=segment_warnings,
                )
            )

        return RoutedDay(
            route_id=day.route_id,
            day=day.day,
            name=day.name,
            geometry=geometry,
            distance_m=distance_m if has_distance else None,
            duration_s=duration_s if has_duration else None,
            engine=self.name,
            warnings=warnings,
            segments=diagnostics,
        )


def make_router(
    engine: str,
    base_url: str | None = None,
    routing_profile: str | None = None,
):
    if engine == "direct":
        return DirectRouter()
    if engine == "osrm":
        return MixedRouter(
            OSRMRouter(
                base_url or "https://router.project-osrm.org",
                profile=routing_profile or "driving",
            )
        )
    if engine == "graphhopper":
        return MixedRouter(GraphHopperRouter(profile=routing_profile or "car"))
    raise ValueError("engine must be direct, osrm or graphhopper")

from __future__ import annotations

from enum import StrEnum
from pydantic import BaseModel, Field


class SegmentMode(StrEnum):
    ROUTE = "route"
    DIRECT = "direct"
    OFF_ROAD = "off-road"
    WALKING = "walking"
    FERRY = "ferry"
    UNKNOWN = "unknown"


class POIType(StrEnum):
    FUEL = "fuel"
    ACCOMMODATION = "accommodation"
    MEDICAL = "medical"
    PASS = "pass"
    VIEWPOINT = "viewpoint"
    CHECKPOST = "checkpost"
    OTHER = "other"


class Waypoint(BaseModel):
    route_id: str = Field(min_length=1)
    day: int = Field(ge=1)
    sequence: int = Field(ge=1)
    name: str = Field(min_length=1)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    segment_mode: SegmentMode = SegmentMode.ROUTE


class POI(BaseModel):
    route_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    poi_type: POIType = POIType.OTHER
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    day: int | None = Field(default=None, ge=1)
    notes: str | None = None


class DayRoute(BaseModel):
    route_id: str
    day: int = Field(ge=1)
    name: str
    waypoints: list[Waypoint] = Field(min_length=1)


class SegmentDiagnostic(BaseModel):
    sequence: int = Field(ge=1)
    start_name: str
    end_name: str
    mode: SegmentMode
    engine: str
    point_count: int = Field(ge=1)
    distance_m: float | None = None
    duration_s: float | None = None
    warnings: list[str] = Field(default_factory=list)


class RoutedDay(BaseModel):
    route_id: str
    day: int
    name: str
    geometry: list[tuple[float, float]] = Field(min_length=1)
    distance_m: float | None = None
    duration_s: float | None = None
    engine: str
    warnings: list[str] = Field(default_factory=list)
    segments: list[SegmentDiagnostic] = Field(default_factory=list)

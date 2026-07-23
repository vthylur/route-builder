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
    elevation_m: float | None = None
    segment_mode: SegmentMode = SegmentMode.ROUTE


class POI(BaseModel):
    route_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    poi_type: POIType = POIType.OTHER
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    elevation_m: float | None = None
    day: int | None = Field(default=None, ge=1)
    notes: str | None = None


class VehicleProfile(BaseModel):
    name: str = Field(min_length=1)
    fuel_capacity_l: float = Field(gt=0)
    reserve_l: float = Field(default=0, ge=0)
    efficiency_kmpl: float = Field(gt=0)
    safety_margin_percent: float = Field(default=15, ge=0, lt=100)

    @property
    def usable_range_km(self) -> float:
        usable_l = max(self.fuel_capacity_l - self.reserve_l, 0)
        nominal = usable_l * self.efficiency_kmpl
        return nominal * (1 - self.safety_margin_percent / 100)


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

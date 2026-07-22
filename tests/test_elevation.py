from __future__ import annotations

import asyncio

import httpx
import pytest

from route_builder.elevation import OpenElevationProvider, enrich_day_elevations, make_elevation_provider
from route_builder.models import DayRoute, Waypoint


class _Client:
    def __init__(self, response: httpx.Response) -> None:
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json=None):
        self.response.request = httpx.Request("POST", url, json=json)
        return self.response


def _day() -> DayRoute:
    return DayRoute(
        route_id="R01",
        day=1,
        name="Elevation_Test",
        waypoints=[
            Waypoint(route_id="R01", day=1, sequence=1, name="A", latitude=12, longitude=77),
            Waypoint(
                route_id="R01",
                day=1,
                sequence=2,
                name="B",
                latitude=13,
                longitude=78,
                elevation_m=1200,
            ),
        ],
    )


def test_open_elevation_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    response = httpx.Response(200, json={"results": [{"elevation": 987.5}]})
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _Client(response))

    provider = OpenElevationProvider("https://elevation.test")
    enriched, result = asyncio.run(enrich_day_elevations(_day(), provider))

    assert enriched.waypoints[0].elevation_m == 987.5
    assert enriched.waypoints[1].elevation_m == 1200
    assert result.requested == 1
    assert result.populated == 1


def test_overwrite_replaces_existing_values(monkeypatch: pytest.MonkeyPatch) -> None:
    response = httpx.Response(
        200,
        json={"results": [{"elevation": 900}, {"elevation": 1300}]},
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _Client(response))

    enriched, result = asyncio.run(
        enrich_day_elevations(_day(), OpenElevationProvider(), overwrite=True)
    )

    assert [point.elevation_m for point in enriched.waypoints] == [900, 1300]
    assert result.populated == 2


def test_unexpected_result_count_is_explicit_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    response = httpx.Response(200, json={"results": []})
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _Client(response))

    with pytest.raises(RuntimeError, match="unexpected result count"):
        asyncio.run(enrich_day_elevations(_day(), OpenElevationProvider()))


def test_elevation_provider_factory() -> None:
    assert make_elevation_provider(None) is None
    assert isinstance(make_elevation_provider("open-elevation"), OpenElevationProvider)
    with pytest.raises(ValueError, match="elevation engine"):
        make_elevation_provider("unknown")

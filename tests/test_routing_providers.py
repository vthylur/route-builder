from __future__ import annotations

import asyncio

import httpx
import pytest

from route_builder.models import DayRoute, Waypoint
from route_builder.routing import GraphHopperRouter, OSRMRouter


def _day() -> DayRoute:
    return DayRoute(
        route_id="R01",
        day=1,
        name="Provider_Test",
        waypoints=[
            Waypoint(route_id="R01", day=1, sequence=1, name="A", latitude=12, longitude=77),
            Waypoint(route_id="R01", day=1, sequence=2, name="B", latitude=13, longitude=78),
        ],
    )


class _Client:
    def __init__(self, response: httpx.Response) -> None:
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params=None):
        self.response.request = httpx.Request("GET", url, params=params)
        return self.response


def test_osrm_success_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    response = httpx.Response(
        200,
        json={
            "code": "Ok",
            "routes": [
                {
                    "distance": 12345.0,
                    "duration": 900.0,
                    "geometry": {"coordinates": [[77.0, 12.0], [78.0, 13.0]]},
                }
            ],
        },
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _Client(response))

    routed = asyncio.run(OSRMRouter("https://example.test").route(_day()))

    assert routed.engine == "osrm"
    assert routed.geometry == [(12.0, 77.0), (13.0, 78.0)]
    assert routed.distance_m == 12345.0
    assert routed.duration_s == 900.0


def test_osrm_no_route_is_explicit_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    response = httpx.Response(200, json={"code": "NoRoute", "message": "Impossible route"})
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _Client(response))

    with pytest.raises(RuntimeError, match="OSRM could not route"):
        asyncio.run(OSRMRouter("https://example.test").route(_day()))


def test_graphhopper_success_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    response = httpx.Response(
        200,
        json={
            "paths": [
                {
                    "distance": 20000.0,
                    "time": 1_800_000,
                    "points": {"coordinates": [[77.0, 12.0], [78.0, 13.0]]},
                }
            ]
        },
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _Client(response))

    routed = asyncio.run(GraphHopperRouter(api_key="test-key").route(_day()))

    assert routed.engine == "graphhopper"
    assert routed.distance_m == 20000.0
    assert routed.duration_s == 1800.0
    assert routed.geometry[-1] == (13.0, 78.0)


def test_graphhopper_missing_paths_is_explicit_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    response = httpx.Response(200, json={"message": "Point not found"})
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _Client(response))

    with pytest.raises(RuntimeError, match="GraphHopper could not route"):
        asyncio.run(GraphHopperRouter(api_key="test-key").route(_day()))


def test_http_error_is_not_silently_converted_to_direct_geometry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = httpx.Response(503, json={"message": "Unavailable"})
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _Client(response))

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(OSRMRouter("https://example.test").route(_day()))

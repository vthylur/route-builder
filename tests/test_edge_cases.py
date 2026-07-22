from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from route_builder.models import DayRoute, Waypoint
from route_builder.parsers import parse_input


def test_rejects_unsupported_input_format(tmp_path: Path) -> None:
    path = tmp_path / "route.txt"
    path.write_text("not an itinerary", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported input"):
        parse_input(path)


def test_rejects_json_array_root(tmp_path: Path) -> None:
    path = tmp_path / "route.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="must be an object"):
        parse_input(path)


def test_rejects_duplicate_sequence_numbers(tmp_path: Path) -> None:
    path = tmp_path / "route.json"
    path.write_text(
        json.dumps(
            {
                "waypoints": [
                    {"route_id": "R", "day": 1, "sequence": 1, "name": "A", "latitude": 12, "longitude": 77},
                    {"route_id": "R", "day": 1, "sequence": 1, "name": "B", "latitude": 13, "longitude": 78},
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Duplicate sequence"):
        parse_input(path)


def test_rejects_out_of_range_coordinates() -> None:
    with pytest.raises(ValidationError):
        Waypoint(
            route_id="R",
            day=1,
            sequence=1,
            name="Invalid",
            latitude=95,
            longitude=77,
        )


def test_single_waypoint_day_is_valid_model() -> None:
    day = DayRoute(
        route_id="R",
        day=1,
        name="Single",
        waypoints=[
            Waypoint(route_id="R", day=1, sequence=1, name="Only", latitude=12, longitude=77)
        ],
    )
    assert len(day.waypoints) == 1


def test_unicode_waypoint_names_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "route.json"
    path.write_text(
        json.dumps(
            {
                "waypoints": [
                    {"route_id": "R", "day": 1, "sequence": 1, "name": "ಬೆಂಗಳೂರು", "latitude": 12.97, "longitude": 77.59},
                    {"route_id": "R", "day": 1, "sequence": 2, "name": "ಲೇಹ್", "latitude": 34.15, "longitude": 77.58},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    day = parse_input(path)[0]
    assert day.waypoints[0].name == "ಬೆಂಗಳೂರು"
    assert day.waypoints[1].name == "ಲೇಹ್"

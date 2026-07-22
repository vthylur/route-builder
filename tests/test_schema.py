from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from route_builder.cli import app
from route_builder.parsers import input_schema_info, parse_input
from route_builder.schema import CURRENT_SCHEMA_VERSION, inspect_schema

runner = CliRunner()


def _payload(schema_version: str | None = CURRENT_SCHEMA_VERSION) -> dict[str, object]:
    payload: dict[str, object] = {
        "waypoints": [
            {
                "route_id": "R01",
                "day": 1,
                "sequence": 1,
                "name": "A",
                "latitude": 12.0,
                "longitude": 77.0,
            },
            {
                "route_id": "R01",
                "day": 1,
                "sequence": 2,
                "name": "B",
                "latitude": 12.1,
                "longitude": 77.1,
            },
        ]
    }
    if schema_version is not None:
        payload["schema_version"] = schema_version
    return payload


def test_current_schema_is_accepted() -> None:
    info = inspect_schema(_payload())
    assert info.effective_version == CURRENT_SCHEMA_VERSION
    assert info.migrated is False
    assert not info.warnings


def test_unversioned_json_is_treated_as_legacy_1_0(tmp_path: Path) -> None:
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps(_payload(None)), encoding="utf-8")

    assert len(parse_input(path)) == 1
    info = input_schema_info(path)
    assert info is not None
    assert info.migrated is True
    assert info.declared_version is None
    assert info.warnings


def test_future_major_schema_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "future.json"
    path.write_text(json.dumps(_payload("2.0")), encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported schema_version"):
        parse_input(path)


def test_invalid_schema_is_rejected() -> None:
    with pytest.raises(ValueError, match="Invalid schema_version"):
        inspect_schema(_payload("latest"))


def test_strict_validation_flags_legacy_unversioned_input(tmp_path: Path) -> None:
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps(_payload(None)), encoding="utf-8")

    result = runner.invoke(app, ["validate", str(path), "--strict"])

    assert result.exit_code == 1
    assert "No schema_version declared" in result.output

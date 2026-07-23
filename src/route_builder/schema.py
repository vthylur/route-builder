from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CURRENT_SCHEMA_VERSION = "1.0"
SUPPORTED_SCHEMA_MAJOR = 1


@dataclass(frozen=True)
class SchemaInfo:
    declared_version: str | None
    effective_version: str
    migrated: bool
    warnings: tuple[str, ...] = ()


def inspect_schema(payload: dict[str, Any]) -> SchemaInfo:
    """Validate a JSON itinerary schema version and describe compatibility handling."""
    raw = payload.get("schema_version")
    if raw in (None, ""):
        return SchemaInfo(
            declared_version=None,
            effective_version=CURRENT_SCHEMA_VERSION,
            migrated=True,
            warnings=(
                "No schema_version declared; interpreted as legacy Route Builder 1.0 input.",
            ),
        )

    version = str(raw).strip()
    parts = version.split(".")
    if not parts[0].isdigit():
        raise ValueError(f"Invalid schema_version: {version!r}")

    major = int(parts[0])
    if major > SUPPORTED_SCHEMA_MAJOR:
        raise ValueError(
            f"Unsupported schema_version {version}; this Route Builder supports "
            f"major version {SUPPORTED_SCHEMA_MAJOR}.x"
        )
    if major < SUPPORTED_SCHEMA_MAJOR:
        raise ValueError(
            f"Unsupported legacy schema_version {version}; migrate it to "
            f"{CURRENT_SCHEMA_VERSION} before building"
        )

    return SchemaInfo(
        declared_version=version,
        effective_version=version,
        migrated=False,
    )

# AGENTS.md

## Product goal
Build a reusable route generator that reads structured itineraries and creates GPX, KML and KMZ outputs using pluggable routing engines.

## Non-negotiable rules
- Never silently replace a failed routed segment with a straight line.
- Preserve route IDs, day boundaries, waypoint order and waypoint names.
- Coordinates use WGS84 decimal degrees in latitude, longitude order internally.
- Keep routing providers isolated from parsers and exporters.
- No API keys in source control; use environment variables.
- Add or update tests for every behavior change.
- Exported files must state which engine created them and include routing warnings.

## Commands
- Install: `pip install -e '.[dev]'`
- Test: `pytest`
- Lint: `ruff check .`
- Generate: `route-builder build examples/sample_routes.csv --engine direct`

## Current milestone
Deliver a reliable CLI MVP with CSV/Excel parsing, direct/OSRM/GraphHopper adapters, GPX/KML/KMZ export and a machine-readable validation report.

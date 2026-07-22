# AGENTS.md

## Product goal
Build a reusable route generator that reads structured itineraries and creates GPX, KML, KMZ and GeoJSON outputs using pluggable routing engines.

## Non-negotiable rules
- Never silently replace a failed routed segment with a straight line.
- Preserve route IDs, day boundaries, waypoint order and waypoint names.
- Coordinates use WGS84 decimal degrees in latitude, longitude order internally.
- Keep routing providers isolated from parsers, intelligence and exporters.
- No API keys in source control; use environment variables.
- Add or update tests for every behavior change.
- Exported files must state which engine created them and include routing warnings.
- Fuel, elevation and safety outputs are planning aids and must state their assumptions.

## Commands
- Install: `pip install -e '.[dev]'`
- Test: `pytest`
- Lint: `ruff check .`
- Validate: `route-builder validate examples/sample_routes.json --strict`
- Generate: `route-builder build examples/sample_routes.json --engine direct`
- Generate with vehicle profile: `route-builder build examples/sample_routes.json --engine direct --vehicle-profile examples/vehicle_ktm390.json`

## Current milestone
Stabilise v0.1: route generation, mixed segments, POIs, manifests, GeoJSON, offline validation, vehicle fuel analysis, elevation summaries, HTML expedition reports, CI and tagged package releases.

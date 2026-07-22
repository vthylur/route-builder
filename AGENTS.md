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
- Segment Mode applies to the segment leaving a waypoint.
- Non-road modes must remain visibly labelled in reports and exports.

## Commands
- Install: `pip install -e '.[dev]'`
- Test: `pytest`
- Lint: `ruff check .`
- Generate: `route-builder build examples/sample_routes.csv --engine direct`

## Current milestone
Strengthen validation and expedition intelligence:
- segment-level failure reporting
- route statistics
- distance sanity checks
- duplicate/near-duplicate waypoint detection
- GeoJSON export
- richer route manifest

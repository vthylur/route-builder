# Route Builder

Route Builder converts structured itinerary waypoints into validated GPX, KML, KMZ and GeoJSON route packages.

## Current capabilities

- CSV, Excel and JSON itinerary input
- Multiple routes and days in one input
- Mixed per-segment routing
- Routing providers: `direct`, `osrm`, and `graphhopper`
- Daily and master GPX files
- Daily and route-level GeoJSON files
- Colour-coded KML/KMZ route folders
- POI layers for fuel, accommodation, medical, passes, viewpoints and checkposts
- Per-segment routing diagnostics
- Route manifests with bounds, totals and segment metadata
- Optional waypoint/POI elevation input and daily elevation summaries
- Vehicle profiles and conservative fuel-range warnings
- Self-contained HTML expedition reports
- Offline input validation for duplicate and suspicious waypoints
- JSON validation reports with failures and warnings
- GitHub Actions CI and tagged release packaging

## Route waypoint columns

| Route ID | Day | Sequence | Name | Latitude | Longitude | Elevation m | Segment Mode |
|---|---:|---:|---|---:|---:|---:|---|

`Elevation m` is optional. `Segment Mode` describes the segment leaving that waypoint and supports `route`, `direct`, `off-road`, `walking`, `ferry`, and `unknown`.

Only `route` is sent to the selected road-routing engine. Other modes are retained as explicitly labelled direct reference geometry rather than silently snapped to an unsuitable road.

## POI input

Excel workbooks may contain a `POIs` sheet with:

| Route ID | Type | Name | Latitude | Longitude | Elevation m | Day | Notes |
|---|---|---|---:|---:|---:|---:|---|

For CSV input, place POIs in a companion file named `<route-file>_pois.csv`. JSON input keeps `waypoints` and `pois` arrays in the same document; see `examples/sample_routes.json`.

## Install

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Validate without routing

```bash
route-builder validate examples/sample_routes.json
route-builder validate routes.xlsx --report validation.json --strict
```

Validation detects duplicate names, duplicate coordinates, near-zero segments and unusually large waypoint gaps. `--strict` returns a non-zero exit code when warnings are present.

## Generate

```bash
route-builder build examples/sample_routes.csv --engine direct --output output
route-builder build examples/sample_routes.json --engine osrm --output output
```

Add fuel intelligence with a vehicle profile:

```bash
route-builder build examples/sample_routes.json \
  --engine osrm \
  --vehicle-profile examples/vehicle_ktm390.json \
  --output output
```

A vehicle profile contains fuel capacity, reserve, expected efficiency and a safety margin. Fuel output is a planning aid only; recorded fuel POIs and availability must be independently verified.

Use a self-hosted OSRM-compatible endpoint:

```bash
route-builder build routes.xlsx --engine osrm --base-url http://localhost:5000
```

GraphHopper:

```bash
set GRAPHHOPPER_API_KEY=your_key
route-builder build routes.xlsx --engine graphhopper --output output
```

Each route output directory contains daily GPX/GeoJSON files, a master GPX, KML, KMZ, route GeoJSON, `manifest.json`, and `report.html`. The output root contains `validation_report.json`.

A routing provider can only follow roads present and connected in its map graph. Route Builder reports failures and non-road segments instead of pretending a straight line is a valid routed road track.

See `AGENTS.md` for Codex development instructions.

# Route Builder

Route Builder converts structured itinerary waypoints into daily GPX tracks and layered KML/KMZ files.

## Current MVP

- CSV and Excel waypoint input
- Multiple routes and days in one input
- Routing providers:
  - `direct` for explicit reference lines only
  - `osrm` for an OSRM-compatible service
  - `graphhopper` using `GRAPHHOPPER_API_KEY`
- One GPX per riding day
- One master GPX per route
- One colour-coded KML/KMZ per route
- JSON validation report with failures and warnings

## Input columns

| Route ID | Day | Sequence | Name | Latitude | Longitude | Segment Mode |
|---|---:|---:|---|---:|---:|---|

`Segment Mode` may be `route` or `direct`. The MVP records this field; segment-level mixed routing is the next implementation milestone.

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

## Generate a reference package

```bash
route-builder build examples/sample_routes.csv --engine direct --output output
```

## Generate using OSRM

```bash
route-builder build examples/sample_routes.csv --engine osrm --output output
```

Use a self-hosted endpoint:

```bash
route-builder build routes.xlsx --engine osrm --base-url http://localhost:5000
```

## Generate using GraphHopper

```bash
set GRAPHHOPPER_API_KEY=your_key
route-builder build routes.xlsx --engine graphhopper --output output
```

## Important limitation

A routing provider can only follow roads present and connected in its map graph. Route Builder reports unroutable sections rather than pretending a straight line is a valid road track.

See `AGENTS.md` for Codex development instructions.

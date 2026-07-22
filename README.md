# Route Builder

Reusable route generation toolkit for converting structured itinerary inputs into routed GPX, KML, and KMZ outputs.

## Goals

- Parse route definitions from Excel or CSV.
- Support interchangeable routing engines such as OSRM and GraphHopper.
- Generate daily and master GPX tracks.
- Generate KML/KMZ files with selectable daily folders and POIs.
- Keep routing, parsing, and exporting modules independent.

## Quick start

```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .[dev]
route-builder --help
```

See `AGENTS.md` for development instructions and `examples/sample_routes.csv` for a starter input format.

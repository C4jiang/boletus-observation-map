#!/usr/bin/env python3
"""Build the complete Laji.fi export for a 1 km ETRS-TM35FIN grid explorer."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from pyproj import Transformer

SOURCE = Path("/Users/zhongkanhong/.hermes/cache/documents/doc_d4e81f3a8e59_laji-data.tsv")
OUT_DIR = Path(__file__).parent / "data"
OUT_CSV = OUT_DIR / "laji_boletus_complete.csv"
OUT_RECORDS = OUT_DIR / "laji_boletus_complete_records.json"
OUT_GRID = OUT_DIR / "laji_boletus_complete_etrs_1km_grid.geojson"
OUT_SUMMARY = OUT_DIR / "summary.json"

GRID_SIZE_METERS = 1_000
TO_WGS84 = Transformer.from_crs("EPSG:3067", "EPSG:4326", always_xy=True)


def grid_key(northing: float, easting: float) -> tuple[int, int]:
    return (int(northing // GRID_SIZE_METERS) * GRID_SIZE_METERS, int(easting // GRID_SIZE_METERS) * GRID_SIZE_METERS)


def grid_id(northing: int, easting: int) -> str:
    return f"ETRS-TM35FIN-1km-N{northing}-E{easting}"


def grid_feature(key: tuple[int, int]) -> dict[str, object]:
    northing, easting = key
    corners_3067 = [
        (easting, northing),
        (easting + GRID_SIZE_METERS, northing),
        (easting + GRID_SIZE_METERS, northing + GRID_SIZE_METERS),
        (easting, northing + GRID_SIZE_METERS),
        (easting, northing),
    ]
    corners_wgs84 = [list(TO_WGS84.transform(east, north)) for east, north in corners_3067]
    return {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [corners_wgs84]},
        "properties": {
            "grid_id": grid_id(northing, easting),
            "northing_min": northing,
            "easting_min": easting,
            "grid_size_m": GRID_SIZE_METERS,
        },
    }


def year_from_date(value: str) -> int | None:
    match = re.match(r"^(\d{4})", value)
    return int(match.group(1)) if match else None


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    grid_keys: set[tuple[int, int]] = set()

    with SOURCE.open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source, delimiter="\t"):
            northing_text = row["ETRS-TM35FIN N"]
            easting_text = row["ETRS-TM35FIN E"]
            latitude_text = row["WGS84 N"]
            longitude_text = row["WGS84 E"]
            northing = float(northing_text) if northing_text else None
            easting = float(easting_text) if easting_text else None
            grid = grid_key(northing, easting) if northing is not None and easting is not None else None
            if grid:
                grid_keys.add(grid)
            records.append({
                "observation_id": row["Observation identifier"],
                "species": row["Species"],
                "scientific_name": row["Scientific name"],
                "date": row["Time"],
                "year": year_from_date(row["Time"]),
                "country": row["Country"],
                "province": row["Biogeographical Province"],
                "accuracy_m": float(row["Location accuracy (m)"]) if row["Location accuracy (m)"] else None,
                "latitude": float(latitude_text) if latitude_text else None,
                "longitude": float(longitude_text) if longitude_text else None,
                "etrs_northing": northing,
                "etrs_easting": easting,
                "reliability": row["Observation Reliability"],
                "collection_quality": row["Quality of collection"],
                "record_type": row["Record type"],
                "source_collection": row["Collection"],
                "grid_id": grid_id(*grid) if grid else None,
            })

    records.sort(key=lambda record: (record["year"] is None, record["date"], record["observation_id"]))
    grid = {
        "type": "FeatureCollection",
        "metadata": {"crs": "EPSG:3067", "grid_size_m": GRID_SIZE_METERS, "grid_cell_count": len(grid_keys)},
        "features": [grid_feature(key) for key in sorted(grid_keys)],
    }
    csv_columns = list(records[0])
    with OUT_CSV.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=csv_columns)
        writer.writeheader()
        writer.writerows(records)
    OUT_RECORDS.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    OUT_GRID.write_text(json.dumps(grid, ensure_ascii=False), encoding="utf-8")

    summary = {
        "source": "Complete Laji.fi TSV export provided by user",
        "recordCount": len(records),
        "mappableRecordCount": sum(record["grid_id"] is not None for record in records),
        "gridCellCount": len(grid_keys),
        "grid": {"crs": "EPSG:3067", "cellSizeMeters": GRID_SIZE_METERS},
        "yearRange": [min(record["year"] for record in records if record["year"] is not None), max(record["year"] for record in records if record["year"] is not None)],
        "accuracy": {
            "missing": sum(record["accuracy_m"] is None for record in records),
            "minimum": min(record["accuracy_m"] for record in records if record["accuracy_m"] is not None),
            "maximum": max(record["accuracy_m"] for record in records if record["accuracy_m"] is not None),
        },
        "scientificNameCounts": dict(sorted(Counter(str(record["scientific_name"]) for record in records).items())),
        "reliabilityCounts": dict(sorted(Counter(str(record["reliability"]) for record in records).items())),
        "recordTypeCounts": dict(sorted(Counter(str(record["record_type"]) for record in records).items())),
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

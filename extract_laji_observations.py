#!/usr/bin/env python3
"""Build a privacy-minimised Finnish Boletus edulis map dataset and 10 km ETRS grid."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from pyproj import Transformer

SOURCE = Path("/Users/zhongkanhong/.hermes/cache/documents/doc_d4e81f3a8e59_laji-data.tsv")
OUT_DIR = Path(__file__).parent / "data"
OUT_CSV = OUT_DIR / "boletus_edulis_laji_2009_50m.csv"
OUT_RECORDS = OUT_DIR / "boletus_edulis_laji_2009_50m_records.json"
OUT_GRID = OUT_DIR / "boletus_edulis_laji_2009_50m_etrs_10km_grid.geojson"
OUT_SUMMARY = OUT_DIR / "summary.json"

SCIENTIFIC_NAME = "Boletus edulis"
MIN_YEAR = 2009
MAX_ACCURACY_METERS = 50.0
GRID_SIZE_METERS = 10_000
SINGLE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TO_WGS84 = Transformer.from_crs("EPSG:3067", "EPSG:4326", always_xy=True)


def grid_key(northing: float, easting: float) -> tuple[int, int]:
    return (int(northing // GRID_SIZE_METERS) * GRID_SIZE_METERS, int(easting // GRID_SIZE_METERS) * GRID_SIZE_METERS)


def grid_feature(key: tuple[int, int], records: list[dict[str, object]]) -> dict[str, object]:
    northing, easting = key
    corners_3067 = [
        (easting, northing),
        (easting + GRID_SIZE_METERS, northing),
        (easting + GRID_SIZE_METERS, northing + GRID_SIZE_METERS),
        (easting, northing + GRID_SIZE_METERS),
        (easting, northing),
    ]
    corners_wgs84 = [list(TO_WGS84.transform(east, north)) for east, north in corners_3067]
    years = [int(record["year"]) for record in records]
    verified = sum(record["reliability"] in {"COMMUNITY_VERIFIED", "EXPERT_VERIFIED"} for record in records)
    return {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [corners_wgs84]},
        "properties": {
            "grid_id": f"ETRS-TM35FIN-10km-N{northing}-E{easting}",
            "northing_min": northing,
            "easting_min": easting,
            "grid_size_m": GRID_SIZE_METERS,
            "observation_count": len(records),
            "verified_count": verified,
            "year_min": min(years),
            "year_max": max(years),
        },
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    with SOURCE.open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source, delimiter="\t"):
            date = row["Time"]
            accuracy = row["Location accuracy (m)"]
            if row["Scientific name"] != SCIENTIFIC_NAME or not accuracy:
                continue
            if not date[:4].isdigit() or int(date[:4]) < MIN_YEAR:
                continue
            if float(accuracy) > MAX_ACCURACY_METERS:
                continue
            if not row["WGS84 N"] or not row["WGS84 E"] or not row["ETRS-TM35FIN N"] or not row["ETRS-TM35FIN E"]:
                continue
            northing = float(row["ETRS-TM35FIN N"])
            easting = float(row["ETRS-TM35FIN E"])
            northing_base, easting_base = grid_key(northing, easting)
            records.append({
                "observation_id": row["Observation identifier"],
                "date": date,
                "year": int(date[:4]),
                "latitude": float(row["WGS84 N"]),
                "longitude": float(row["WGS84 E"]),
                "accuracy_m": float(accuracy),
                "reliability": row["Observation Reliability"],
                "record_type": row["Record type"],
                "source_collection": row["Collection"],
                "province": row["Biogeographical Province"],
                "grid_id": f"ETRS-TM35FIN-10km-N{northing_base}-E{easting_base}",
            })

    records.sort(key=lambda record: (str(record["date"]), str(record["observation_id"])))
    grid_records: dict[tuple[int, int], list[dict[str, object]]] = defaultdict(list)
    for record in records:
        match = re.fullmatch(r"ETRS-TM35FIN-10km-N(\d+)-E(\d+)", str(record["grid_id"]))
        assert match
        grid_records[(int(match.group(1)), int(match.group(2)))].append(record)

    grid = {
        "type": "FeatureCollection",
        "metadata": {"crs": "EPSG:3067", "grid_size_m": GRID_SIZE_METERS, "record_count": len(records)},
        "features": [grid_feature(key, grid_records[key]) for key in sorted(grid_records)],
    }
    csv_columns = [
        "observation_id", "date", "year", "latitude", "longitude", "accuracy_m", "reliability",
        "record_type", "source_collection", "province", "grid_id",
    ]
    with OUT_CSV.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=csv_columns)
        writer.writeheader()
        writer.writerows(records)
    OUT_RECORDS.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    OUT_GRID.write_text(json.dumps(grid, ensure_ascii=False), encoding="utf-8")

    summary = {
        "source": "Laji.fi TSV export provided by user",
        "recordCount": len(records),
        "gridCellCount": len(grid_records),
        "filters": {
            "scientificName": SCIENTIFIC_NAME,
            "minimumYear": MIN_YEAR,
            "maximumLocationAccuracyMeters": MAX_ACCURACY_METERS,
            "country": "Finland",
        },
        "reliabilityCounts": dict(sorted(Counter(str(record["reliability"]) for record in records).items())),
        "preciseSingleDateCount": sum(bool(SINGLE_DATE.fullmatch(str(record["date"]))) for record in records),
        "yearCounts": dict(sorted(Counter(int(record["year"]) for record in records).items())),
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

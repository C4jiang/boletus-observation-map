#!/usr/bin/env python3
"""Extract the strict, high-precision Boletus edulis study sample."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

SOURCE = Path(
    "/Users/zhongkanhong/homebase/00_inbox/machine-learning/04_dataset/"
    "0014982-260903145123482.csv"
)
OUT_DIR = Path(__file__).parent / "data"
OUT_CSV = OUT_DIR / "boletus_edulis_fi_2009_high_precision.csv"
OUT_GEOJSON = OUT_DIR / "boletus_edulis_fi_2009_high_precision.geojson"
OUT_SUMMARY = OUT_DIR / "summary.json"

TARGET_TAXON_KEY = "MCH9"
TARGET_SCIENTIFIC_NAME = "Boletus edulis Bull."
MAX_UNCERTAINTY_METERS = 1000.0
MIN_YEAR = 2009


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []

    with SOURCE.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, delimiter="\t")
        for row in reader:
            if row["taxonKey"] != TARGET_TAXON_KEY:
                continue
            if row["scientificName"] != TARGET_SCIENTIFIC_NAME:
                continue
            if not row["year"] or int(row["year"]) < MIN_YEAR:
                continue
            if (
                not row["coordinateUncertaintyInMeters"]
                or float(row["coordinateUncertaintyInMeters"]) > MAX_UNCERTAINTY_METERS
            ):
                continue
            rows.append(row)

    rows.sort(key=lambda row: (row["eventDate"], row["gbifID"]))

    fieldnames = list(rows[0])
    with OUT_CSV.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    features = []
    for row in rows:
        properties = {
            "gbifID": row["gbifID"],
            "eventDate": row["eventDate"],
            "year": int(row["year"]),
            "countryCode": row["countryCode"],
            "locality": row["locality"],
            "stateProvince": row["stateProvince"],
            "basisOfRecord": row["basisOfRecord"],
            "coordinateUncertaintyInMeters": float(row["coordinateUncertaintyInMeters"]),
            "recordedBy": row["recordedBy"],
            "catalogNumber": row["catalogNumber"],
        }
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(row["decimalLongitude"]), float(row["decimalLatitude"])],
                },
                "properties": properties,
            }
        )

    geojson = {
        "type": "FeatureCollection",
        "metadata": {
            "targetTaxonKey": TARGET_TAXON_KEY,
            "targetScientificName": TARGET_SCIENTIFIC_NAME,
            "minimumYear": MIN_YEAR,
            "maximumCoordinateUncertaintyMeters": MAX_UNCERTAINTY_METERS,
            "recordCount": len(features),
        },
        "features": features,
    }
    OUT_GEOJSON.write_text(json.dumps(geojson, ensure_ascii=False), encoding="utf-8")

    country_counts = Counter(row["countryCode"] for row in rows)
    year_counts = Counter(int(row["year"]) for row in rows)
    summary = {
        "recordCount": len(rows),
        "filters": {
            "taxonKey": TARGET_TAXON_KEY,
            "scientificName": TARGET_SCIENTIFIC_NAME,
            "minimumYear": MIN_YEAR,
            "maximumCoordinateUncertaintyMeters": MAX_UNCERTAINTY_METERS,
        },
        "countryCounts": dict(sorted(country_counts.items())),
        "yearCounts": dict(sorted(year_counts.items())),
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

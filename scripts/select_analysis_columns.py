#!/usr/bin/env python3
"""Keep analysis columns and add EPSG:3067 coordinates for FMI rainfall grids."""

import csv
from pathlib import Path

from pyproj import Transformer

INPUT = Path(__file__).parent.parent / "data" / "boletus_edulis_vs_other_agaricoid_balanced.tsv"
OUTPUT = Path(__file__).parent.parent / "data" / "boletus_edulis_vs_other_agaricoid_analysis.tsv"
COLUMNS = [
    "sample_group",
    "scientific_name",
    "event_datetime",
    "latitude_wgs84",
    "longitude_wgs84",
    "etrs_tm35fin_easting_m",
    "etrs_tm35fin_northing_m",
    "coordinate_accuracy_m",
]
TO_TM35FIN = Transformer.from_crs("EPSG:4326", "EPSG:3067", always_xy=True)


def main():
    total = 0
    with INPUT.open(encoding="utf-8", newline="") as source, OUTPUT.open("w", encoding="utf-8", newline="") as output:
        reader = csv.DictReader(source, delimiter="\t")
        writer = csv.DictWriter(output, fieldnames=COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in reader:
            longitude = float(row["decimalLongitude"])
            latitude = float(row["decimalLatitude"])
            easting, northing = TO_TM35FIN.transform(longitude, latitude)
            writer.writerow(
                {
                    "sample_group": row["sample_group"],
                    "scientific_name": row["scientificName"],
                    "event_datetime": row["eventDate"],
                    "latitude_wgs84": latitude,
                    "longitude_wgs84": longitude,
                    "etrs_tm35fin_easting_m": round(easting, 3),
                    "etrs_tm35fin_northing_m": round(northing, 3),
                    "coordinate_accuracy_m": row["coordinateAccuracy"],
                }
            )
            total += 1
    print(f"Wrote {total} rows to {OUTPUT}")


if __name__ == "__main__":
    main()

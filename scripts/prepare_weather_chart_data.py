#!/usr/bin/env python3
"""Prepare complete-weather records and draw monthly grouped observation counts."""

import csv
import os
import tempfile
from collections import Counter
from pathlib import Path

INPUT = Path(__file__).parent.parent / "data" / "boletus_edulis_vs_other_agaricoid_weather.tsv"
CHART = Path(__file__).parent.parent / "data" / "boletus_edulis_vs_other_agaricoid_weather_by_month_grouped.png"
TARGET_SPECIES = "Boletus edulis"
INDICATOR_COLUMN = "Has Boletus edulis"
PARTITION_COLUMN = "longitude_partition"
MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def prepare_rows(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[str]]:
    """Keep rows complete across supplied weather features and add a binary target."""
    if not rows:
        return [], []
    weather_columns = [
        column
        for column in rows[0]
        if column.startswith("temp_") or column.startswith("rain_") or column.startswith("rainy_")
    ]
    kept = [row.copy() for row in rows if all((row.get(column) or "").strip() for column in weather_columns)]
    for row in kept:
        row[INDICATOR_COLUMN] = "1" if row["scientific_name"].strip() == TARGET_SPECIES else "0"
    return kept, weather_columns


def partition_rows_by_longitude(rows: list[dict[str, str]], group_count: int = 5) -> list[dict[str, str]]:
    """Label longitude-ordered records in near-equal contiguous partitions."""
    if group_count < 1:
        raise ValueError("group_count must be positive")
    ordered = sorted((row.copy() for row in rows), key=lambda row: float(row["longitude_wgs84"]))
    base_size, remainder = divmod(len(ordered), group_count)
    start = 0
    for group in range(1, group_count + 1):
        size = base_size + (group <= remainder)
        for row in ordered[start : start + size]:
            row[PARTITION_COLUMN] = str(group)
        start += size
    return ordered


def write_rows(rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    """Atomically replace the derived TSV, preserving a stable column order."""
    output_fields = [
        fieldname
        for fieldname in fieldnames
        if fieldname not in {INDICATOR_COLUMN, PARTITION_COLUMN}
    ] + [INDICATOR_COLUMN, PARTITION_COLUMN]
    fd, temporary_name = tempfile.mkstemp(prefix=f"{INPUT.name}.", suffix=".tmp", dir=INPUT.parent, text=True)
    os.close(fd)
    try:
        with open(temporary_name, "w", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=output_fields, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary_name, INPUT)
    except Exception:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def draw_grouped_month_chart(rows: list[dict[str, str]]) -> None:
    """Draw monthly observation counts with one bar per target group."""
    import matplotlib.pyplot as plt

    counts = Counter((int(row["event_month"]), row[INDICATOR_COLUMN]) for row in rows)
    months = list(range(1, 13))
    other = [counts[(month, "0")] for month in months]
    edulis = [counts[(month, "1")] for month in months]

    plt.style.use("seaborn-v0_8-whitegrid")
    figure, axis = plt.subplots(figsize=(13, 7), dpi=180)
    width = 0.38
    axis.bar([month - width / 2 for month in months], other, width=width, color="#5B7DB1", label="Other agaricoid fungi (0)")
    axis.bar([month + width / 2 for month in months], edulis, width=width, color="#E28A3B", label="Boletus edulis (1)")
    axis.set_title("Observations by Month", pad=14, weight="bold")
    axis.set_xlabel("Month")
    axis.set_ylabel("Number of observations")
    axis.set_xticks(months, MONTH_LABELS)
    axis.legend(title=INDICATOR_COLUMN, frameon=True)
    axis.spines[["top", "right"]].set_visible(False)
    figure.tight_layout()
    figure.savefig(CHART, bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    with INPUT.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source, delimiter="\t")
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    if "event_month" not in fieldnames:
        raise ValueError("event_month is required; run build_weather_features.py first")

    prepared, weather_columns = prepare_rows(rows)
    partitioned = partition_rows_by_longitude(prepared)
    write_rows(partitioned, fieldnames)
    draw_grouped_month_chart(partitioned)
    edulis = sum(row[INDICATOR_COLUMN] == "1" for row in partitioned)
    print(f"Input rows: {len(rows)}")
    print(f"Removed rows with incomplete weather: {len(rows) - len(prepared)}")
    print(f"Output rows: {len(prepared)}")
    print(f"Boletus edulis: {edulis}; other agaricoid: {len(prepared) - edulis}")
    print(f"Weather columns: {', '.join(weather_columns)}")
    print(f"Wrote chart: {CHART}")


if __name__ == "__main__":
    main()

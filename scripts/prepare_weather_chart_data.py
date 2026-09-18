#!/usr/bin/env python3
"""Prepare complete-weather records and draw monthly grouped observation counts."""

import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

INPUT = Path(__file__).parent.parent / "data" / "boletus_edulis_vs_other_agaricoid_weather.tsv"
CHART = Path(__file__).parent.parent / "data" / "boletus_edulis_vs_other_agaricoid_weather_by_month_grouped.png"
TARGET_SPECIES = "Boletus edulis"
INDICATOR_COLUMN = "Has Boletus edulis"
PARTITION_COLUMN = "longitude_partition"
MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def prepare_weather_dataframe(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Keep complete weather rows and add a numeric Boletus indicator."""
    weather_columns = [
        column
        for column in frame.columns
        if column.startswith("temp_") or column.startswith("rain_") or column.startswith("rainy_")
    ]
    prepared = frame.replace(r"^\s*$", pd.NA, regex=True).dropna(subset=weather_columns).copy()
    prepared[INDICATOR_COLUMN] = (prepared["scientific_name"].str.strip() == TARGET_SPECIES).astype("int8")
    return prepared, weather_columns


def prepare_rows(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[str]]:
    """Compatibility wrapper for callers that still use records rather than frames."""
    prepared, weather_columns = prepare_weather_dataframe(pd.DataFrame(rows))
    records = prepared.copy()
    records[INDICATOR_COLUMN] = records[INDICATOR_COLUMN].astype(str)
    return records.to_dict(orient="records"), weather_columns


def partition_weather_dataframe(frame: pd.DataFrame, group_count: int = 5) -> pd.DataFrame:
    """Label longitude-ordered rows in near-equal contiguous partitions."""
    if group_count < 1:
        raise ValueError("group_count must be positive")
    ordered = frame.copy()
    ordered["_longitude"] = pd.to_numeric(ordered["longitude_wgs84"], errors="raise")
    ordered = ordered.sort_values("_longitude", kind="stable").drop(columns="_longitude").reset_index(drop=True)
    base_size, remainder = divmod(len(ordered), group_count)
    sizes = [base_size + (group <= remainder) for group in range(1, group_count + 1)]
    ordered[PARTITION_COLUMN] = np.repeat(np.arange(1, group_count + 1, dtype="int8"), sizes)
    return ordered


def partition_rows_by_longitude(rows: list[dict[str, str]], group_count: int = 5) -> list[dict[str, str]]:
    """Compatibility wrapper for callers that still use records rather than frames."""
    partitioned = partition_weather_dataframe(pd.DataFrame(rows), group_count)
    records = partitioned.copy()
    records[PARTITION_COLUMN] = records[PARTITION_COLUMN].astype(str)
    return records.to_dict(orient="records")


def write_dataframe(frame: pd.DataFrame, fieldnames: list[str]) -> None:
    """Atomically replace the derived TSV, preserving a stable column order."""
    output_fields = [
        fieldname
        for fieldname in fieldnames
        if fieldname not in {INDICATOR_COLUMN, PARTITION_COLUMN}
    ] + [INDICATOR_COLUMN, PARTITION_COLUMN]
    fd, temporary_name = tempfile.mkstemp(prefix=f"{INPUT.name}.", suffix=".tmp", dir=INPUT.parent, text=True)
    os.close(fd)
    try:
        frame.loc[:, output_fields].to_csv(temporary_name, sep="\t", index=False, lineterminator="\n")
        os.replace(temporary_name, INPUT)
    except Exception:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def draw_grouped_month_chart(frame: pd.DataFrame) -> None:
    """Draw monthly observation counts with one bar per target group."""
    import matplotlib.pyplot as plt

    counts = frame.groupby(["event_month", INDICATOR_COLUMN]).size().unstack(fill_value=0).reindex(range(1, 13), fill_value=0)
    other = counts.get(0, pd.Series(0, index=counts.index)).tolist()
    edulis = counts.get(1, pd.Series(0, index=counts.index)).tolist()
    months = list(range(1, 13))

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
    frame = pd.read_csv(INPUT, sep="\t")
    fieldnames = frame.columns.tolist()
    if "event_month" not in fieldnames:
        raise ValueError("event_month is required; run build_weather_features.py first")

    prepared, weather_columns = prepare_weather_dataframe(frame)
    partitioned = partition_weather_dataframe(prepared)
    write_dataframe(partitioned, fieldnames)
    draw_grouped_month_chart(partitioned)
    edulis = int(partitioned[INDICATOR_COLUMN].sum())
    print(f"Input rows: {len(frame)}")
    print(f"Removed rows with incomplete weather: {len(frame) - len(prepared)}")
    print(f"Output rows: {len(prepared)}")
    print(f"Boletus edulis: {edulis}; other agaricoid: {len(prepared) - edulis}")
    print(f"Weather columns: {', '.join(weather_columns)}")
    print(f"Wrote chart: {CHART}")


if __name__ == "__main__":
    main()

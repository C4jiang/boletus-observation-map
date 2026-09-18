#!/usr/bin/env python3
"""Render Finland observations and longitude-balanced partition boundaries."""

import argparse
import json
import math
from pathlib import Path
from urllib.request import urlretrieve

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent
INPUT = PROJECT_ROOT / "data" / "boletus_edulis_vs_other_agaricoid_weather.tsv"
OUTPUT = PROJECT_ROOT / "data" / "boletus_edulis_finland_longitude_partitions_map.png"
BOUNDARY_CACHE = PROJECT_ROOT / "data" / "ne_10m_admin_0_countries.geojson"
NATURAL_EARTH_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_0_countries.geojson"
TARGET_COLUMN = "Has Boletus edulis"
PARTITION_COLUMN = "longitude_partition"
LEGEND_LOCATION = "upper left"


def as_dataframe(rows: pd.DataFrame | list[dict[str, str]]) -> pd.DataFrame:
    """Normalize callers using either a dataframe or record dictionaries."""
    return rows.copy() if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)


def longitude_cut_lines(rows: pd.DataFrame | list[dict[str, str]]) -> list[float]:
    """Return midpoint longitudes separating consecutive partition labels."""
    frame = as_dataframe(rows)
    ranges = frame.assign(
        _longitude=pd.to_numeric(frame["longitude_wgs84"], errors="raise"),
        _partition=pd.to_numeric(frame[PARTITION_COLUMN], errors="raise"),
    ).groupby("_partition", sort=True)["_longitude"].agg(["min", "max"])
    return [
        (ranges.loc[left, "max"] + ranges.loc[right, "min"]) / 2
        for left, right in zip(ranges.index, ranges.index[1:])
    ]


def fetch_boundary(refresh: bool) -> Path:
    """Cache Natural Earth's public-domain country boundary data locally."""
    if refresh or not BOUNDARY_CACHE.exists():
        BOUNDARY_CACHE.parent.mkdir(parents=True, exist_ok=True)
        urlretrieve(NATURAL_EARTH_URL, BOUNDARY_CACHE)
    return BOUNDARY_CACHE


def finland_geometry(boundary_path: Path) -> dict:
    """Extract Finland's GeoJSON geometry from a Natural Earth country file."""
    with boundary_path.open(encoding="utf-8") as source:
        data = json.load(source)
    for feature in data["features"]:
        properties = feature.get("properties", {})
        if properties.get("ADMIN") == "Finland":
            return feature["geometry"]
    raise ValueError("Finland boundary not found in Natural Earth data")


def polygons(geometry: dict) -> list[list[list[float]]]:
    """Normalize Polygon and MultiPolygon coordinate structures into polygons."""
    if geometry["type"] == "Polygon":
        return geometry["coordinates"]
    if geometry["type"] == "MultiPolygon":
        return [ring for polygon in geometry["coordinates"] for ring in polygon]
    raise ValueError(f"Unsupported geometry type: {geometry['type']}")


def plot(frame: pd.DataFrame, geometry: dict) -> None:
    """Save the national outline, all observations, and partition cut lines."""
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    figure, axis = plt.subplots(figsize=(10, 14), dpi=220)
    for ring in polygons(geometry):
        longitudes, latitudes = zip(*ring)
        axis.fill(longitudes, latitudes, color="#EDF2F5", zorder=0)
        axis.plot(longitudes, latitudes, color="#4D5965", linewidth=0.55, zorder=1)

    other = frame.loc[frame[TARGET_COLUMN] == 0]
    edulis = frame.loc[frame[TARGET_COLUMN] == 1]
    axis.scatter(
        other["longitude_wgs84"],
        other["latitude_wgs84"],
        s=7,
        color="#4C78A8",
        alpha=0.62,
        linewidths=0,
        zorder=3,
        label="Other agaricoid fungi (0)",
    )
    axis.scatter(
        edulis["longitude_wgs84"],
        edulis["latitude_wgs84"],
        s=8,
        color="#E45756",
        alpha=0.72,
        linewidths=0,
        zorder=4,
        label="Boletus edulis (1)",
    )
    for cut in longitude_cut_lines(frame):
        axis.axvline(cut, color="#2F3E46", linestyle="--", linewidth=1.05, alpha=0.9, zorder=2)

    axis.set_xlim(19.0, 32.0)
    axis.set_ylim(59.4, 70.3)
    axis.set_aspect(1 / math.cos(math.radians(64.5)))
    axis.set_xlabel("Longitude (°E)")
    axis.set_ylabel("Latitude (°N)")
    axis.set_title("Finnish mushroom observations by longitude partition", pad=14, weight="bold")
    boundary_proxy = Line2D([0], [0], color="#2F3E46", linestyle="--", linewidth=1.05, label="Longitude partition boundary")
    handles, labels = axis.get_legend_handles_labels()
    axis.legend(handles + [boundary_proxy], labels + [boundary_proxy.get_label()], loc=LEGEND_LOCATION, frameon=True)
    axis.grid(color="#AAB7C4", alpha=0.22, linewidth=0.5)
    figure.tight_layout()
    figure.savefig(OUTPUT, bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-boundary", action="store_true", help="redownload the cached Natural Earth boundary")
    arguments = parser.parse_args()

    frame = pd.read_csv(INPUT, sep="\t")
    required = {"latitude_wgs84", "longitude_wgs84", TARGET_COLUMN, PARTITION_COLUMN}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    geometry = finland_geometry(fetch_boundary(arguments.refresh_boundary))
    plot(frame, geometry)
    print(f"Plotted {len(frame)} observations to {OUTPUT}")
    print("Longitude cut lines: " + ", ".join(f"{cut:.6f}" for cut in longitude_cut_lines(frame)))


if __name__ == "__main__":
    main()

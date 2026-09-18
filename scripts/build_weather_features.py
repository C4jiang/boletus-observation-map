#!/usr/bin/env python3
"""Append trailing weather features from FMI 1 km daily grids to mushroom data."""

import csv
from contextlib import ExitStack
from datetime import date, datetime, timedelta
from pathlib import Path

import h5py
import numpy as np

INPUT = Path(__file__).parent.parent / "data" / "boletus_edulis_vs_other_agaricoid_analysis.tsv"
CLIMATE_DIR = Path(__file__).parent.parent / "data" / "fmi_gridded_obs_daily_1km"
OUTPUT = Path(__file__).parent.parent / "data" / "boletus_edulis_vs_other_agaricoid_weather.tsv"
WINDOW_DAYS = 30
RAINY_DAY_THRESHOLD_MM = 0.0
VARIABLES = {
    "tmean": ("Tday", "tday", "Tday"),
    "tmin": ("Tmin", "tmin", "Tmin"),
    "tmax": ("Tmax", "tmax", "Tmax"),
    "rain": ("RRday", "rrday", "RRday"),
}
FEATURE_COLUMNS = [
    "temp_mean_7d",
    "temp_mean_14d",
    "temp_mean_30d",
    "temp_min_7d",
    "temp_max_7d",
    "rain_mean_7d",
    "rain_mean_14d",
    "rain_mean_30d",
    "rainy_days_14d",
]
OUTPUT_COLUMNS = [
    "sample_group",
    "scientific_name",
    "latitude_wgs84",
    "longitude_wgs84",
    "etrs_tm35fin_easting_m",
    "etrs_tm35fin_northing_m",
    "coordinate_accuracy_m",
    *FEATURE_COLUMNS,
    "event_year",
    "event_month",
    "day_of_year",
]


def weather_day_index(day_indices: dict[date, int], day: date, layer_count: int) -> int | None:
    """Return a valid layer index, or None when this variable lacks that day."""
    index = day_indices.get(day)
    return index if index is not None and index < layer_count else None


def weather_dataset_name(keys: object, expected_name: str) -> str:
    """Support FMI's upper- and lowercase dataset names across export years."""
    available = set(keys)
    if expected_name in available:
        return expected_name
    if expected_name.lower() in available:
        return expected_name.lower()
    raise KeyError(f"Missing weather dataset {expected_name!r}; found {sorted(available)}")


def fill_value_from_attribute(value: object) -> float:
    """Return a NetCDF fill value whether h5py exposes it as a scalar or array."""
    return float(np.asarray(value).reshape(-1)[0])


def event_date_from_interval(value: str) -> date:
    """Use the end date of an ISO-like observation interval."""
    return datetime.fromisoformat(value.split("/")[-1]).date()


def nearest_grid_indices(grid_values: np.ndarray, coordinates: np.ndarray) -> np.ndarray:
    """Return each coordinate's nearest 1 km grid-coordinate index."""
    return np.abs(grid_values[:, None] - coordinates[None, :]).argmin(axis=0)


def summarize_features(tmean: np.ndarray, tmin: np.ndarray, tmax: np.ndarray, rain: np.ndarray) -> dict[str, float | int | None]:
    """Compute inclusive trailing-window features; incomplete windows become None."""
    def complete(values: np.ndarray) -> bool:
        return len(values) and np.isfinite(values).all()

    def mean(values: np.ndarray) -> float | None:
        return float(np.mean(values)) if complete(values) else None

    def minimum(values: np.ndarray) -> float | None:
        return float(np.min(values)) if complete(values) else None

    def maximum(values: np.ndarray) -> float | None:
        return float(np.max(values)) if complete(values) else None

    rain_14d = rain[-14:]
    return {
        "temp_mean_7d": mean(tmean[-7:]),
        "temp_mean_14d": mean(tmean[-14:]),
        "temp_mean_30d": mean(tmean[-30:]),
        "temp_min_7d": minimum(tmin[-7:]),
        "temp_max_7d": maximum(tmax[-7:]),
        "rain_mean_7d": mean(rain[-7:]),
        "rain_mean_14d": mean(rain[-14:]),
        "rain_mean_30d": mean(rain[-30:]),
        "rainy_days_14d": int(np.sum(rain_14d > RAINY_DAY_THRESHOLD_MM)) if complete(rain_14d) else None,
    }


def climate_path(variable: tuple[str, str, str], year: int) -> Path:
    directory, filename_prefix, _ = variable
    return CLIMATE_DIR / directory / f"{filename_prefix}_{year}.nc"


def dates_since_epoch(values: np.ndarray) -> dict[date, int]:
    epoch = date(1970, 1, 1)
    return {epoch + timedelta(days=int(value)): index for index, value in enumerate(values)}


def write_output(rows: list[dict[str, str]], event_dates: list[date], daily_values: dict[str, np.ndarray]) -> int:
    complete_rows = 0
    with OUTPUT.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=OUTPUT_COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for index, row in enumerate(rows):
            features = summarize_features(
                daily_values["tmean"][index],
                daily_values["tmin"][index],
                daily_values["tmax"][index],
                daily_values["rain"][index],
            )
            complete_rows += all(features[name] is not None for name in FEATURE_COLUMNS)
            output_row = {column: row[column] for column in OUTPUT_COLUMNS[:7]}
            output_row["event_year"] = str(event_dates[index].year)
            output_row["event_month"] = str(event_dates[index].month)
            output_row["day_of_year"] = event_dates[index].timetuple().tm_yday
            output_row.update({name: "" if value is None else round(value, 4) for name, value in features.items()})
            writer.writerow(output_row)
    return complete_rows


def main() -> None:
    with INPUT.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source, delimiter="\t"))

    event_dates = [event_date_from_interval(row["event_datetime"]) for row in rows]
    reference_file = climate_path(VARIABLES["rain"], 2010)
    with h5py.File(reference_file, "r") as climate:
        eastings = climate["easting"][:]
        northings = climate["northing"][:]

    easting_values = np.array([float(row["etrs_tm35fin_easting_m"]) for row in rows])
    northing_values = np.array([float(row["etrs_tm35fin_northing_m"]) for row in rows])
    easting_indices = nearest_grid_indices(eastings, easting_values)
    northing_indices = nearest_grid_indices(northings, northing_values)
    distances = np.hypot(eastings[easting_indices] - easting_values, northings[northing_indices] - northing_values)
    if distances.max() > 750:
        raise ValueError(f"A coordinate is more than 750 m from its nearest FMI grid point: {distances.max():.1f} m")

    daily_values = {name: np.full((len(rows), WINDOW_DAYS), np.nan) for name in VARIABLES}
    scheduled_dates: dict[date, list[tuple[int, int]]] = {}
    for record_index, event_day in enumerate(event_dates):
        for offset in range(WINDOW_DAYS):
            day = event_day - timedelta(days=WINDOW_DAYS - 1 - offset)
            scheduled_dates.setdefault(day, []).append((record_index, offset))

    for year in sorted({day.year for day in scheduled_dates}):
        paths = {name: climate_path(variable, year) for name, variable in VARIABLES.items()}
        if not all(path.exists() for path in paths.values()):
            continue
        with ExitStack() as stack:
            files = {name: stack.enter_context(h5py.File(path, "r")) for name, path in paths.items()}
            day_indices = {name: dates_since_epoch(climate["time"][:]) for name, climate in files.items()}
            for day, assignments in scheduled_dates.items():
                if day.year != year:
                    continue
                record_indices = np.array([record_index for record_index, _ in assignments])
                offsets = np.array([offset for _, offset in assignments])
                for name, climate in files.items():
                    dataset_name = weather_dataset_name(climate.keys(), VARIABLES[name][2])
                    dataset = climate[dataset_name]
                    layer_index = weather_day_index(day_indices[name], day, dataset.shape[0])
                    if layer_index is None:
                        continue
                    layer = dataset[layer_index, :, :]
                    values = layer[northing_indices[record_indices], easting_indices[record_indices]].astype(float)
                    fill_value = fill_value_from_attribute(dataset.attrs["_FillValue"])
                    values[values == fill_value] = np.nan
                    daily_values[name][record_indices, offsets] = values

    complete_rows = write_output(rows, event_dates, daily_values)
    print(f"Wrote {len(rows)} rows to {OUTPUT}")
    print(f"Rows with all weather features: {complete_rows}")
    print(f"Maximum point-to-grid distance: {distances.max():.1f} m")


if __name__ == "__main__":
    main()

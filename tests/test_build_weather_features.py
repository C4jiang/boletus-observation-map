from datetime import date
import csv

import numpy as np

import scripts.build_weather_features as weather_features
from scripts.build_weather_features import (
    event_date_from_interval,
    nearest_grid_indices,
    summarize_features,
    fill_value_from_attribute,
    weather_dataset_name,
    weather_day_index,
    OUTPUT_COLUMNS,
    VARIABLES,
)


def test_output_includes_month_and_non_missing_calendar_columns():
    assert OUTPUT_COLUMNS[-3:] == ["event_year", "event_month", "day_of_year"]


def test_weather_day_index_requires_a_present_time_and_data_layer():
    day = date(2026, 9, 7)
    assert weather_day_index({day: 248}, day, 249) == 248
    assert weather_day_index({day: 249}, day, 249) is None
    assert weather_day_index({}, day, 249) is None


def test_weather_dataset_name_accepts_upper_and_lowercase_fmi_versions():
    assert weather_dataset_name(["Tday", "time"], "Tday") == "Tday"
    assert weather_dataset_name(["tday", "time"], "Tday") == "tday"


def test_fill_value_from_attribute_accepts_a_single_value_array():
    assert fill_value_from_attribute(np.array([-1.1754940241844054e38])) == -1.1754940241844054e38


def test_weather_variables_separate_file_prefix_from_dataset_name():
    assert VARIABLES["tmean"] == ("Tday", "tday", "Tday")
    assert VARIABLES["tmin"] == ("Tmin", "tmin", "Tmin")
    assert VARIABLES["tmax"] == ("Tmax", "tmax", "Tmax")
    assert VARIABLES["rain"] == ("RRday", "rrday", "RRday")


def test_event_date_uses_the_end_of_a_datetime_interval():
    assert event_date_from_interval("2025-08-30T14:49/2025-08-30T23:19") == date(2025, 8, 30)


def test_nearest_grid_indices_handles_descending_northing_coordinates():
    indices = nearest_grid_indices(np.array([7000.0, 6000.0, 5000.0]), np.array([6100.0, 4900.0]))
    assert indices.tolist() == [1, 2]


def test_summarize_features_uses_inclusive_trailing_windows():
    temperatures = np.arange(1.0, 31.0)
    features = summarize_features(
        tmean=temperatures,
        tmin=temperatures - 10,
        tmax=temperatures + 10,
        rain=np.arange(30.0),
    )

    assert features["temp_mean_7d"] == 27.0
    assert features["temp_mean_14d"] == 23.5
    assert features["temp_mean_30d"] == 15.5
    assert features["temp_min_7d"] == 14.0
    assert features["temp_max_7d"] == 40.0
    assert features["rain_mean_7d"] == 26.0
    assert features["rain_mean_14d"] == 22.5
    assert features["rain_mean_30d"] == 14.5
    assert features["rainy_days_14d"] == 14


def test_write_output_populates_event_month(tmp_path, monkeypatch):
    output = tmp_path / "weather.tsv"
    monkeypatch.setattr(weather_features, "OUTPUT", output)
    daily_values = {name: np.arange(1.0, 31.0).reshape(1, 30) for name in VARIABLES}
    row = {
        "sample_group": "boletus_edulis",
        "scientific_name": "Boletus edulis",
        "latitude_wgs84": "60.0",
        "longitude_wgs84": "24.0",
        "etrs_tm35fin_easting_m": "500000",
        "etrs_tm35fin_northing_m": "6650000",
        "coordinate_accuracy_m": "100",
    }

    weather_features.write_output([row], [date(2025, 8, 30)], daily_values)

    with output.open(newline="", encoding="utf-8") as source:
        written = next(csv.DictReader(source, delimiter="\t"))
    assert written["event_month"] == "8"

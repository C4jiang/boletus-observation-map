import pandas as pd

from scripts.plot_finland_longitude_partitions import LEGEND_LOCATION, longitude_cut_lines


def test_legend_is_placed_at_upper_left():
    assert LEGEND_LOCATION == "upper left"


def test_longitude_cut_lines_use_midpoints_between_adjacent_partitions():
    rows = [
        {"longitude_wgs84": "20.0", "longitude_partition": "1"},
        {"longitude_wgs84": "21.0", "longitude_partition": "1"},
        {"longitude_wgs84": "22.0", "longitude_partition": "2"},
        {"longitude_wgs84": "23.5", "longitude_partition": "2"},
        {"longitude_wgs84": "24.0", "longitude_partition": "3"},
    ]

    assert longitude_cut_lines(rows) == [21.5, 23.75]


def test_longitude_cut_lines_accepts_a_dataframe():
    frame = pd.DataFrame(
        {
            "longitude_wgs84": [20.0, 21.0, 22.0, 23.5, 24.0],
            "longitude_partition": [1, 1, 2, 2, 3],
        }
    )

    assert longitude_cut_lines(frame) == [21.5, 23.75]

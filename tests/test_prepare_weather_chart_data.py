from scripts.prepare_weather_chart_data import partition_rows_by_longitude, prepare_rows


def test_prepare_rows_discards_missing_weather_and_adds_boletus_indicator():
    rows = [
        {
            "scientific_name": "Boletus edulis",
            "temp_mean_7d": "14.2",
            "rain_mean_7d": "2.1",
            "event_month": "8",
        },
        {
            "scientific_name": "Amanita muscaria",
            "temp_mean_7d": "",
            "rain_mean_7d": "1.3",
            "event_month": "9",
        },
        {
            "scientific_name": "Russula claroflava",
            "temp_mean_7d": "11.0",
            "rain_mean_7d": "0.8",
            "event_month": "9",
        },
    ]

    kept, weather_columns = prepare_rows(rows)

    assert weather_columns == ["temp_mean_7d", "rain_mean_7d"]
    assert [row["Has Boletus edulis"] for row in kept] == ["1", "0"]
    assert [row["scientific_name"] for row in kept] == ["Boletus edulis", "Russula claroflava"]


def test_partition_rows_by_longitude_balances_five_groups():
    rows = [
        {"longitude_wgs84": str(longitude), "id": str(longitude)}
        for longitude in [25, 20, 24, 21, 23, 22, 19, 18, 17, 16, 15]
    ]

    partitioned = partition_rows_by_longitude(rows, group_count=5)

    counts = [sum(row["longitude_partition"] == str(group) for row in partitioned) for group in range(1, 6)]
    assert counts == [3, 2, 2, 2, 2]
    assert [row["id"] for row in sorted(partitioned, key=lambda row: float(row["longitude_wgs84"]))] == [str(i) for i in range(15, 26)]

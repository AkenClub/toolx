from plugins.worklog.plugin import (
    DEFAULT_DAY_TOTAL_HOURS,
    calculate_duration_hours,
    calculate_percentage,
    ensure_day,
    load_worklog_data,
    save_worklog_data,
    summarize_day,
)


def test_calculate_duration_hours_returns_hours():
    assert calculate_duration_hours("09:00", "10:30") == 1.5


def test_invalid_time_range_returns_zero():
    assert calculate_duration_hours("10:00", "10:00") == 0.0
    assert calculate_duration_hours("10:30", "10:00") == 0.0


def test_calculate_percentage_uses_day_total():
    assert calculate_percentage(3.75, 7.5) == 50.0


def test_ensure_day_creates_defaults():
    data = {"days": {}}

    day = ensure_day(data, "2026-04-15")

    assert day["day_total_hours"] == DEFAULT_DAY_TOTAL_HOURS
    assert day["items"] == []


def test_summarize_day_marks_complete():
    items = [
        {"start_time": "09:00", "end_time": "12:45", "duration_hours": 3.75},
        {"start_time": "13:30", "end_time": "17:15", "duration_hours": 3.75},
    ]

    summary = summarize_day(items, 7.5)

    assert summary["total_hours"] == 7.5
    assert summary["percentage"] == 100.0
    assert summary["difference_hours"] == 0.0
    assert summary["status"] == "刚好 100%"


def test_summarize_day_flags_invalid_rows():
    items = [
        {"start_time": "09:00", "end_time": "09:00", "duration_hours": 0.0},
    ]

    summary = summarize_day(items, 7.5)

    assert summary["invalid_count"] == 1
    assert summary["status"] == "未满 100%"


def test_load_corrupted_json_recovers_empty(tmp_path):
    data_file = tmp_path / "data.json"
    data_file.write_text("{broken", encoding="utf-8")

    loaded, corrupted = load_worklog_data(str(data_file))

    assert corrupted is True
    assert loaded == {"days": {}}


def test_save_and_load_roundtrip(tmp_path):
    data_file = tmp_path / "data.json"
    expected = {
        "days": {
            "2026-04-15": {
                "day_total_hours": 7.5,
                "items": [
                    {
                        "id": "row-1",
                        "date": "2026-04-15",
                        "start_time": "09:00",
                        "end_time": "10:30",
                        "task_text": "Implement plugin",
                        "duration_hours": 1.5,
                    }
                ],
            }
        }
    }

    save_worklog_data(str(data_file), expected)
    loaded, corrupted = load_worklog_data(str(data_file))

    assert corrupted is False
    assert loaded == expected

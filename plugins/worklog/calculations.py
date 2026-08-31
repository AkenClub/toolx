import math
import uuid

from PyQt6.QtCore import QTime


DEFAULT_DAY_TOTAL_HOURS = 7.5
DEFAULT_START_TIME = "09:00"
DEFAULT_END_TIME = "09:30"
DEFAULT_TASK_DURATION_MINUTES = 30
COMPLETE_TOLERANCE_HOURS = 0.01
DEFAULT_LUNCH_BREAK_START_TIME = "12:00"
DEFAULT_LUNCH_BREAK_END_TIME = "13:30"
LUNCH_BREAK_CONFIG_KEY = "worklog_lunch_break"
MAX_CUSTOM_DURATION_HOURS = 24.0


def ensure_data_shape(data):
    if not isinstance(data, dict):
        return {"days": {}}

    days = data.get("days")
    if not isinstance(days, dict):
        days = {}

    return {"days": days}


def parse_time_text(time_text, fallback_text):
    parsed_time = QTime.fromString(str(time_text), "HH:mm")
    if parsed_time.isValid():
        return parsed_time.toString("HH:mm")
    return fallback_text


def parse_time_value(time_text):
    parsed_time = QTime.fromString(str(time_text), "HH:mm")
    if parsed_time.isValid():
        return parsed_time
    return None


def time_to_seconds(time_value):
    return (time_value.hour() * 3600) + (time_value.minute() * 60) + time_value.second()


def get_lunch_break_settings(config_manager=None):
    raw_settings = {}
    if config_manager is not None:
        raw_settings = config_manager.get(LUNCH_BREAK_CONFIG_KEY, {})

    if not isinstance(raw_settings, dict):
        raw_settings = {}

    start_text = parse_time_text(raw_settings.get("start_time"), DEFAULT_LUNCH_BREAK_START_TIME)
    end_text = parse_time_text(raw_settings.get("end_time"), DEFAULT_LUNCH_BREAK_END_TIME)
    start_time = parse_time_value(start_text)
    end_time = parse_time_value(end_text)

    return {
        "start_time": start_text,
        "end_time": end_text,
        "is_valid": bool(start_time and end_time and end_time > start_time),
    }


def is_valid_lunch_break(lunch_start_text, lunch_end_text):
    lunch_start_time = parse_time_value(lunch_start_text)
    lunch_end_time = parse_time_value(lunch_end_text)
    return bool(lunch_start_time and lunch_end_time and lunch_end_time > lunch_start_time)


def calculate_lunch_break_overlap_seconds(start_time, end_time, lunch_start_text, lunch_end_text):
    lunch_start_time = parse_time_value(lunch_start_text)
    lunch_end_time = parse_time_value(lunch_end_text)
    if not lunch_start_time or not lunch_end_time or lunch_end_time <= lunch_start_time:
        return 0

    start_seconds = time_to_seconds(start_time)
    end_seconds = time_to_seconds(end_time)
    lunch_start_seconds = time_to_seconds(lunch_start_time)
    lunch_end_seconds = time_to_seconds(lunch_end_time)

    overlap_start = max(start_seconds, lunch_start_seconds)
    overlap_end = min(end_seconds, lunch_end_seconds)
    return max(0, overlap_end - overlap_start)


def calculate_duration_details(
    start_text,
    end_text,
    lunch_start_text=DEFAULT_LUNCH_BREAK_START_TIME,
    lunch_end_text=DEFAULT_LUNCH_BREAK_END_TIME,
):
    start_time = parse_time_value(start_text)
    end_time = parse_time_value(end_text)
    lunch_settings_valid = is_valid_lunch_break(lunch_start_text, lunch_end_text)

    if not start_time or not end_time or end_time <= start_time:
        return {
            "is_valid_range": False,
            "raw_hours": 0.0,
            "lunch_break_hours": 0.0,
            "duration_hours": 0.0,
            "lunch_break_applied": False,
            "lunch_break_valid": lunch_settings_valid,
        }

    raw_seconds = start_time.secsTo(end_time)
    lunch_break_seconds = calculate_lunch_break_overlap_seconds(
        start_time,
        end_time,
        lunch_start_text,
        lunch_end_text,
    )
    duration_seconds = max(0, raw_seconds - lunch_break_seconds)

    return {
        "is_valid_range": True,
        "raw_hours": round(raw_seconds / 3600.0, 2),
        "lunch_break_hours": round(lunch_break_seconds / 3600.0, 2),
        "duration_hours": round(duration_seconds / 3600.0, 2),
        "lunch_break_applied": lunch_break_seconds > 0,
        "lunch_break_valid": lunch_settings_valid,
    }


def adjust_time_for_lunch_break(time_text, lunch_start_text, lunch_end_text):
    current_time = parse_time_value(time_text)
    lunch_start_time = parse_time_value(lunch_start_text)
    lunch_end_time = parse_time_value(lunch_end_text)
    if not current_time or not lunch_start_time or not lunch_end_time or lunch_end_time <= lunch_start_time:
        return time_text

    if lunch_start_time <= current_time < lunch_end_time:
        return lunch_end_time.toString("HH:mm")
    return current_time.toString("HH:mm")


def add_work_minutes(start_text, minutes, lunch_start_text, lunch_end_text):
    start_time = parse_time_value(start_text)
    lunch_start_time = parse_time_value(lunch_start_text)
    lunch_end_time = parse_time_value(lunch_end_text)
    if not start_time:
        return DEFAULT_END_TIME

    current_time = parse_time_value(adjust_time_for_lunch_break(start_text, lunch_start_text, lunch_end_text))
    if not current_time:
        return DEFAULT_END_TIME

    if not lunch_start_time or not lunch_end_time or lunch_end_time <= lunch_start_time:
        return current_time.addSecs(minutes * 60).toString("HH:mm")

    remaining_seconds = minutes * 60
    if current_time < lunch_start_time:
        seconds_before_lunch = current_time.secsTo(lunch_start_time)
        if remaining_seconds <= seconds_before_lunch:
            return current_time.addSecs(remaining_seconds).toString("HH:mm")
        remaining_seconds -= seconds_before_lunch
        current_time = lunch_end_time

    return current_time.addSecs(remaining_seconds).toString("HH:mm")


def normalize_custom_duration(value):
    if value is None:
        return None
    try:
        duration = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(duration) or duration < 0 or duration > MAX_CUSTOM_DURATION_HOURS:
        return None
    return round(duration, 2)


def normalize_boolean(value):
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def create_task_item(
    date_key,
    start_time=DEFAULT_START_TIME,
    end_time=DEFAULT_END_TIME,
    task_text="",
    lunch_start_text=DEFAULT_LUNCH_BREAK_START_TIME,
    lunch_end_text=DEFAULT_LUNCH_BREAK_END_TIME,
):
    start_text = parse_time_text(start_time, DEFAULT_START_TIME)
    end_text = parse_time_text(end_time, DEFAULT_END_TIME)
    return {
        "id": str(uuid.uuid4()),
        "date": date_key,
        "start_time": start_text,
        "end_time": end_text,
        "task_text": task_text or "",
        "is_registered": False,
        "custom_duration_hours": None,
        "duration_hours": calculate_duration_hours(
            start_text,
            end_text,
            lunch_start_text,
            lunch_end_text,
        ),
    }


def get_next_task_time_range(
    items,
    lunch_start_text=DEFAULT_LUNCH_BREAK_START_TIME,
    lunch_end_text=DEFAULT_LUNCH_BREAK_END_TIME,
):
    if not items:
        return DEFAULT_START_TIME, DEFAULT_END_TIME

    last_item = items[-1] if isinstance(items[-1], dict) else {}
    start_time = parse_time_value(last_item.get("end_time", ""))
    if start_time is None:
        return DEFAULT_START_TIME, DEFAULT_END_TIME

    start_text = adjust_time_for_lunch_break(
        start_time.toString("HH:mm"),
        lunch_start_text,
        lunch_end_text,
    )
    end_text = add_work_minutes(
        start_text,
        DEFAULT_TASK_DURATION_MINUTES,
        lunch_start_text,
        lunch_end_text,
    )
    return start_text, end_text


def normalize_task_item(
    item,
    date_key,
    lunch_start_text=DEFAULT_LUNCH_BREAK_START_TIME,
    lunch_end_text=DEFAULT_LUNCH_BREAK_END_TIME,
):
    if not isinstance(item, dict):
        item = {}

    start_text = parse_time_text(item.get("start_time"), DEFAULT_START_TIME)
    end_text = parse_time_text(item.get("end_time"), DEFAULT_END_TIME)
    custom_duration_hours = normalize_custom_duration(item.get("custom_duration_hours"))
    auto_duration = calculate_duration_hours(
        start_text,
        end_text,
        lunch_start_text,
        lunch_end_text,
    )

    return {
        "id": str(item.get("id") or uuid.uuid4()),
        "date": date_key,
        "start_time": start_text,
        "end_time": end_text,
        "task_text": str(item.get("task_text") or ""),
        "is_registered": normalize_boolean(item.get("is_registered")),
        "custom_duration_hours": custom_duration_hours,
        "duration_hours": custom_duration_hours if custom_duration_hours is not None else auto_duration,
    }


def ensure_day(
    data,
    date_key,
    lunch_start_text=DEFAULT_LUNCH_BREAK_START_TIME,
    lunch_end_text=DEFAULT_LUNCH_BREAK_END_TIME,
):
    if not isinstance(data, dict):
        raise TypeError("worklog data must be a dict")

    normalized = ensure_data_shape(data)
    data.clear()
    data.update(normalized)

    day = data["days"].get(date_key)
    if not isinstance(day, dict):
        day = {}

    raw_day_total_hours = day.get("day_total_hours", DEFAULT_DAY_TOTAL_HOURS)
    try:
        day_total_hours = round(float(raw_day_total_hours), 2)
    except (TypeError, ValueError):
        day_total_hours = DEFAULT_DAY_TOTAL_HOURS
    if not math.isfinite(day_total_hours):
        day_total_hours = DEFAULT_DAY_TOTAL_HOURS

    raw_items = day.get("items", [])
    if not isinstance(raw_items, list):
        raw_items = []

    items = [
        normalize_task_item(item, date_key, lunch_start_text, lunch_end_text)
        for item in raw_items
    ]

    normalized_day = {
        "day_total_hours": day_total_hours,
        "items": items,
    }
    data["days"][date_key] = normalized_day
    return normalized_day


def calculate_duration_hours(
    start_text,
    end_text,
    lunch_start_text=DEFAULT_LUNCH_BREAK_START_TIME,
    lunch_end_text=DEFAULT_LUNCH_BREAK_END_TIME,
):
    return calculate_duration_details(
        start_text,
        end_text,
        lunch_start_text,
        lunch_end_text,
    )["duration_hours"]


def calculate_percentage(duration_hours, day_total_hours):
    try:
        duration = float(duration_hours)
        total_hours = float(day_total_hours)
    except (TypeError, ValueError):
        return 0.0

    if not math.isfinite(duration) or not math.isfinite(total_hours) or duration < 0 or total_hours <= 0:
        return 0.0
    return round((duration / total_hours) * 100, 2)


def summarize_day(
    items,
    day_total_hours,
    lunch_start_text=DEFAULT_LUNCH_BREAK_START_TIME,
    lunch_end_text=DEFAULT_LUNCH_BREAK_END_TIME,
):
    detail_rows = []
    for item in items:
        if not isinstance(item, dict):
            item = {}
        detail = calculate_duration_details(
            item.get("start_time", ""),
            item.get("end_time", ""),
            lunch_start_text,
            lunch_end_text,
        )
        custom_duration = normalize_custom_duration(item.get("custom_duration_hours"))
        if custom_duration is not None:
            # 手动覆盖是明确的业务选择，不再重复统计时间段中的午休扣除。
            detail["duration_hours"] = custom_duration
            detail["is_valid_range"] = True
            detail["lunch_break_hours"] = 0.0
            detail["lunch_break_applied"] = False
        detail_rows.append(detail)

    total_hours = round(sum(detail["duration_hours"] for detail in detail_rows), 2)
    invalid_count = sum(1 for detail in detail_rows if not detail["is_valid_range"])
    lunch_break_hours = round(sum(detail["lunch_break_hours"] for detail in detail_rows), 2)
    lunch_break_applied_count = sum(1 for detail in detail_rows if detail["lunch_break_applied"])
    lunch_break_valid = (
        all(detail["lunch_break_valid"] for detail in detail_rows)
        if detail_rows
        else is_valid_lunch_break(lunch_start_text, lunch_end_text)
    )

    try:
        target_hours = round(float(day_total_hours), 2)
    except (TypeError, ValueError):
        target_hours = 0.0
    if not math.isfinite(target_hours):
        target_hours = 0.0

    if target_hours <= 0:
        return {
            "total_hours": total_hours,
            "percentage": 0.0,
            "difference_hours": round(total_hours - target_hours, 2),
            "status": "标准工时无效",
            "color": "#e6a23c",
            "invalid_count": invalid_count,
            "lunch_break_hours": lunch_break_hours,
            "lunch_break_applied_count": lunch_break_applied_count,
            "lunch_break_valid": lunch_break_valid,
        }

    difference_hours = round(total_hours - target_hours, 2)
    percentage = round((total_hours / target_hours) * 100, 2)

    if abs(difference_hours) <= COMPLETE_TOLERANCE_HOURS:
        status = "刚好 100%"
        color = "#67c23a"
    elif difference_hours < 0:
        status = "未满 100%"
        color = "#e6a23c"
    else:
        status = "超过 100%"
        color = "#f56c6c"

    return {
        "total_hours": total_hours,
        "percentage": percentage,
        "difference_hours": difference_hours,
        "status": status,
        "color": color,
        "invalid_count": invalid_count,
        "lunch_break_hours": lunch_break_hours,
        "lunch_break_applied_count": lunch_break_applied_count,
        "lunch_break_valid": lunch_break_valid,
    }

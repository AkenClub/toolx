# Worklog Plugin Design

**Date:** 2026-04-15

**Goal:** Add a new ToolX plugin for daily task and work-hour tracking that supports multiple entries per day, exact start/end times, automatic duration calculation, per-day percentage summaries, date switching, and immediate local persistence that survives app restarts.

## Background

The current ToolX application already supports lightweight plugin loading through `plugins/<plugin_name>/plugin.py` and persistent global configuration through `toolx_config.json`. The new worklog feature is business data rather than global app configuration, so it should be isolated in its own plugin-local storage file.

The user needs to:

- Record multiple tasks per day
- Enter exact time ranges for each task
- Have hours calculated automatically from the time range
- Set a per-day standard work-hour target, defaulting to `7.5`
- See each task's percentage of the day's standard hours
- See whether the day sums to `100%`
- Get warnings when totals do not match `100%`, without being blocked
- Switch dates and maintain a history of records
- Keep data saved locally in real time, not only on app exit

## Chosen Approach

Use a dedicated plugin under `plugins/worklog/` backed by a plugin-local JSON file such as `plugins/worklog/data.json`.

This approach is preferred over storing the data inside `toolx_config.json` because:

- Worklog records are domain data, not app settings
- The JSON structure can grow over time without polluting global config
- Import/export and future reporting features will be easier to add
- Failure or corruption can be isolated to this plugin

SQLite is intentionally not used because the current requirement is small, local, and single-user. JSON keeps the implementation lightweight and aligned with the existing project style.

## Scope

### In Scope

- A new sidebar plugin entry for worklog management
- Per-day worklog records keyed by date
- Multiple task rows per day
- Exact start time and end time per row
- Automatic duration calculation in hours
- Automatic percentage calculation against the day's standard hours
- A configurable per-day standard hours input, default `7.5`
- A daily summary area showing totals and status
- Date switching to view and edit history
- Immediate save on every meaningful change
- Local persistence in a plugin-owned JSON file

### Out of Scope

- CSV or Excel export
- Monthly or weekly aggregate reporting
- Charts or dashboards
- Cross-day tasks that automatically split over midnight
- Collaboration or sync
- Undo/redo history

## Plugin Structure

Create a new plugin directory:

```text
plugins/
└── worklog/
    ├── plugin.py
    └── data.json   # created on demand
```

The plugin should follow the same loading pattern as existing ToolX plugins:

- implement `PluginInterface`
- expose `get_plugin(config_manager)`
- lazily create its widget through `get_widget(parent)`

## Data Model

The plugin should store data grouped by day.

Recommended JSON structure:

```json
{
  "days": {
    "2026-04-15": {
      "day_total_hours": 7.5,
      "items": [
        {
          "id": "f1a3a6bc-1f34-4ad8-9b40-0d2fbe6dcb55",
          "date": "2026-04-15",
          "start_time": "09:00",
          "end_time": "10:30",
          "task_text": "Implement worklog plugin",
          "duration_hours": 1.5
        }
      ]
    }
  }
}
```

### Field Definitions

- `days`: top-level mapping of ISO date strings to daily worklog records
- `day_total_hours`: the standard number of hours for the selected date, default `7.5`
- `items`: ordered list of task entries for that date
- `id`: unique row identifier for delete/update stability
- `date`: ISO date string matching the owning day
- `start_time`: `HH:mm`
- `end_time`: `HH:mm`
- `task_text`: freeform task description
- `duration_hours`: computed numeric value stored with the row

### Derived Values

The following values should be calculated in memory, not treated as source-of-truth persisted fields:

- per-row percentage
- daily summed hours
- daily percentage total
- delta from target
- status label

This avoids duplicated state drifting out of sync with the stored times.

## UI Design

The worklog plugin UI should use the same visual tone as the existing plugins and remain simple, clean, and productivity-focused.

### Top Controls

At the top of the page:

- A date selector, defaulting to the current date
- A standard-hours input for the selected day, default `7.5`
- An `新增任务` button to append a blank task row for the current date

Behavior:

- Changing the selected date loads that day's data immediately
- If the day does not exist yet, it is initialized with `day_total_hours = 7.5` and an empty task list
- Changing the day's standard hours recalculates all percentages and immediately saves

### Task Table

The center of the page should present a table-like editor with one row per task.

Each row contains:

- Start time editor
- End time editor
- Read-only duration column
- Read-only percentage column
- Task description editor
- Delete button

Row behavior:

- Time editors should allow exact time selection
- Duration is computed from end minus start
- Percentage is computed from duration divided by the selected day's standard hours
- Editing any field should trigger recalculation and immediate save
- Deleting a row should remove it from the current date and immediately save

### Summary Area

The bottom of the page should show a per-day summary card with:

- Standard hours
- Summed recorded hours
- Percentage used
- Difference from the daily target
- Status text

Status colors:

- below `100%`: orange warning
- exactly `100%`: green success
- above `100%`: red warning

The summary is informative only. It must never block saving.

## Calculation Rules

### Duration

Each task duration is computed strictly from:

`duration_hours = end_time - start_time`

Requirements:

- format to two decimal places for display
- store numeric duration in hours
- do not allow a manually edited duration field

### Percentage

Per-row percentage:

`duration_hours / day_total_hours * 100`

Daily total percentage:

`sum(duration_hours) / day_total_hours * 100`

Display values should be rounded to two decimal places.

## Validation Rules

### Time Range Validation

If `end_time <= start_time`:

- the row is invalid
- the row duration is treated as `0`
- the row percentage is treated as `0`
- the UI shows a visible warning that end time must be later than start time
- the row still remains editable and is still saved

This is intentional because the user may temporarily create incomplete or invalid rows while editing, and the plugin must not discard or block data entry.

### Standard Hours Validation

If the selected day's standard hours is empty, zero, or negative:

- per-row percentage displays as `0%`
- daily total percentage displays as `0%`
- the summary shows a warning that standard hours is invalid
- the record still saves

## Persistence Strategy

The plugin must save to local disk immediately after:

- changing the selected day's standard hours
- changing a row's start time
- changing a row's end time
- changing a row's task text
- adding a row
- deleting a row
- switching dates after the current in-memory edits have been applied

Persistence requirements:

- file path should resolve relative to the plugin module location so it works in development and packaged builds
- if `data.json` does not exist, create it on first save
- writes should serialize the full current data structure in UTF-8 JSON

## Error Handling

### Data File Missing

If the data file does not exist:

- start with an empty structure
- create the file on the first successful save

### Data File Corrupted

If the JSON file cannot be parsed:

- show a one-time error message to the user
- recover to an empty in-memory structure
- allow the user to continue working

The plugin does not need automatic backup rotation in this phase.

### Save Failure

If the file cannot be written:

- show an error message
- keep the current in-memory state intact

## Interaction Flow

### Opening the Plugin

When the user opens the plugin:

- the widget loads today's date
- the plugin loads all stored data from local JSON
- the current day's record is displayed
- if the day does not exist, a default empty day is prepared

### Creating a Task

When the user clicks `新增任务`:

- append a new row for the selected date
- initialize with an empty task description
- initialize with a deterministic default time range of `09:00` to `09:30`
- immediately save the day data

### Editing a Task

When the user edits start time, end time, or task text:

- update the row
- recalculate duration and percentages
- refresh the summary card
- immediately save to disk

### Switching Dates

When the user changes the date:

- ensure current edits are already reflected in memory
- load or initialize the destination day
- refresh table and summary

## Architecture Notes

The implementation should keep responsibilities separated inside `plugins/worklog/plugin.py` even if it remains a single file for now:

- storage helpers for loading/saving JSON
- normalization helpers for missing or invalid day data
- duration/percentage calculation helpers
- widget logic for rendering and event wiring
- plugin wrapper implementing `PluginInterface`

This keeps the file maintainable and makes future extraction into multiple files straightforward if the plugin grows.

## Testing Strategy

The project currently has a `tests/` directory, so this feature should add focused coverage around the worklog rules.

### Required Test Coverage

- loading empty data
- loading corrupted JSON
- creating a new day with default `7.5` hours
- duration calculation from valid start/end times
- invalid time range producing `0` hours
- per-row percentage calculation
- daily summary calculation
- date switching preserving different days' records
- save/load roundtrip of multiple task rows

### Manual Verification

Manual QA should verify:

- the plugin appears in the sidebar
- today's date loads by default
- rows can be added and deleted
- editing any field updates the summary immediately
- closing and reopening the app preserves all entered data
- switching dates shows distinct records
- below, equal, and above `100%` states use the correct color/status

## Non-Goals and Deferred Enhancements

The following are explicitly deferred:

- export to external reporting formats
- task templates
- search and filtering
- total views across multiple days
- auto-splitting entries across midnight
- stronger recovery features such as automatic backups

## Acceptance Criteria

The feature is complete when all of the following are true:

- A new worklog plugin is visible in the ToolX sidebar
- The plugin lets the user select a date and edit that date's records
- A day can contain multiple task rows
- Each row has start time, end time, computed duration, computed percentage, and task text
- Daily standard hours default to `7.5` and can be changed per date
- Percentages and summaries recalculate immediately after edits
- Totals not equal to `100%` are clearly indicated but do not block saving
- Data persists to a local file without relying on window close behavior
- Reopening the app restores previous records

## Precision Rule

To avoid floating-point noise causing unstable status labels:

- duration values should be stored and displayed rounded to two decimal places
- summary totals should be rounded to two decimal places before display
- the day should be treated as exactly complete when the absolute difference between `sum(duration_hours)` and `day_total_hours` is less than or equal to `0.01`

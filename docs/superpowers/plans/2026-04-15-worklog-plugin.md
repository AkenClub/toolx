# Worklog Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a ToolX worklog plugin that records per-day task entries with exact start/end times, automatic duration calculation, percentage summaries, date switching, and immediate local JSON persistence.

**Architecture:** Add a new `plugins/worklog/plugin.py` that contains a small storage layer, calculation helpers, and a PyQt6 widget for editing per-day task rows. Keep business data in `plugins/worklog/data.json`, integrate the plugin with the existing loader and packaging config, and cover the storage/calculation rules with focused pytest tests.

**Tech Stack:** Python 3, PyQt6, pytest, JSON file persistence, existing ToolX plugin system

---

### Task 1: Add the plugin module and package integration

**Files:**
- Create: `plugins/worklog/plugin.py`
- Modify: `ToolX.spec`

- [ ] **Step 1: Write the failing packaging expectation**

```python
# The packaged app must include the new plugin import.
# Hidden import to add in ToolX.spec:
'plugins.worklog.plugin'
```

- [ ] **Step 2: Confirm the current spec is missing it**

Run: `rg -n "plugins\\.worklog\\.plugin" ToolX.spec`
Expected: no matches

- [ ] **Step 3: Add the hidden import**

```python
hiddenimports=[
    'plugins.quick_copy.plugin',
    'plugins.about.plugin',
    'plugins.settings.plugin',
    'plugins.worklog.plugin'
],
```

- [ ] **Step 4: Create the new plugin wrapper and core helpers**

```python
class WorklogPlugin(PluginInterface):
    def __init__(self, config_manager=None):
        super().__init__(config_manager)
        self.widget = None

    def get_id(self) -> str:
        return "worklog"

    def get_name(self) -> str:
        return "任务工时"

    def get_icon(self):
        return "🕒"

    def get_widget(self, parent: QWidget) -> QWidget:
        if self.widget is None:
            self.widget = WorklogWidget(parent)
        return self.widget

def get_plugin(config_manager):
    return WorklogPlugin(config_manager)
```

- [ ] **Step 5: Commit**

```bash
git add ToolX.spec plugins/worklog/plugin.py
git commit -m "feat: add worklog plugin shell"
```

### Task 2: Implement local storage and calculation helpers

**Files:**
- Modify: `plugins/worklog/plugin.py`
- Test: `tests/test_worklog_plugin.py`

- [ ] **Step 1: Write failing tests for storage and calculations**

```python
def test_calculate_duration_hours():
    assert calculate_duration_hours("09:00", "10:30") == 1.5

def test_invalid_time_range_returns_zero():
    assert calculate_duration_hours("10:00", "10:00") == 0.0

def test_ensure_day_defaults():
    data = {"days": {}}
    day = ensure_day(data, "2026-04-15")
    assert day["day_total_hours"] == 7.5
    assert day["items"] == []
```

- [ ] **Step 2: Run targeted tests to verify they fail**

Run: `pytest tests/test_worklog_plugin.py -q`
Expected: FAIL because helper functions do not exist yet

- [ ] **Step 3: Add minimal helper implementations**

```python
def ensure_data_shape(data):
    if not isinstance(data, dict):
        return {"days": {}}
    days = data.get("days")
    if not isinstance(days, dict):
        days = {}
    return {"days": days}

def ensure_day(data, date_key):
    data = ensure_data_shape(data)
    day = data["days"].setdefault(date_key, {"day_total_hours": 7.5, "items": []})
    if not isinstance(day.get("items"), list):
        day["items"] = []
    if not isinstance(day.get("day_total_hours"), (int, float)):
        day["day_total_hours"] = 7.5
    return day

def calculate_duration_hours(start_text, end_text):
    start = QTime.fromString(start_text, "HH:mm")
    end = QTime.fromString(end_text, "HH:mm")
    if not start.isValid() or not end.isValid() or end <= start:
        return 0.0
    return round(start.secsTo(end) / 3600.0, 2)
```

- [ ] **Step 4: Add load/save helpers with corruption recovery**

```python
def load_worklog_data(data_file):
    if not os.path.exists(data_file):
        return {"days": {}}, False
    try:
        with open(data_file, "r", encoding="utf-8") as f:
            return ensure_data_shape(json.load(f)), False
    except Exception:
        return {"days": {}}, True

def save_worklog_data(data_file, data):
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(ensure_data_shape(data), f, indent=2, ensure_ascii=False)
```

- [ ] **Step 5: Re-run targeted tests**

Run: `pytest tests/test_worklog_plugin.py -q`
Expected: PASS for helper tests

- [ ] **Step 6: Commit**

```bash
git add plugins/worklog/plugin.py tests/test_worklog_plugin.py
git commit -m "feat: add worklog storage helpers"
```

### Task 3: Build the editable worklog UI with immediate save

**Files:**
- Modify: `plugins/worklog/plugin.py`

- [ ] **Step 1: Add the main widget layout**

```python
self.date_edit = QDateEdit()
self.day_total_spin = QDoubleSpinBox()
self.add_row_button = QPushButton("新增任务")
self.table = QTableWidget(0, 6)
self.summary_label = QLabel()
```

- [ ] **Step 2: Wire date switching and default day loading**

```python
today = QDate.currentDate()
self.date_edit.setDate(today)
self.current_date_key = today.toString("yyyy-MM-dd")
self.load_day_into_table(self.current_date_key)
self.date_edit.dateChanged.connect(self.on_date_changed)
```

- [ ] **Step 3: Add row creation and cell widgets**

```python
def add_task_row(self, item=None):
    row = self.table.rowCount()
    self.table.insertRow(row)
    start_edit = QTimeEdit(QTime.fromString(item["start_time"], "HH:mm"))
    end_edit = QTimeEdit(QTime.fromString(item["end_time"], "HH:mm"))
    task_edit = QPlainTextEdit(item["task_text"])
    delete_button = QPushButton("删除")
```

- [ ] **Step 4: Recalculate row and summary on every edit**

```python
def on_row_changed(self, row):
    item = self.collect_row_data(row)
    item["duration_hours"] = calculate_duration_hours(item["start_time"], item["end_time"])
    self.update_row_display(row, item)
    self.write_current_day_to_memory()
    self.save_data()
    self.refresh_summary()
```

- [ ] **Step 5: Add summary status logic**

```python
def summarize_day(items, day_total_hours):
    total = round(sum(item["duration_hours"] for item in items), 2)
    percent = round((total / day_total_hours) * 100, 2) if day_total_hours > 0 else 0.0
    delta = round(total - day_total_hours, 2)
    if abs(delta) <= 0.01:
        status = "刚好 100%"
    elif delta < 0:
        status = "未满 100%"
    else:
        status = "超过 100%"
    return total, percent, delta, status
```

- [ ] **Step 6: Verify the UI loads**

Run: `python main.py`
Expected: sidebar shows `任务工时`, changing any value updates the summary immediately, reopening the app preserves records in `plugins/worklog/data.json`

- [ ] **Step 7: Commit**

```bash
git add plugins/worklog/plugin.py plugins/worklog/data.json
git commit -m "feat: add worklog editor UI"
```

### Task 4: Add focused regression tests

**Files:**
- Modify: `tests/test_worklog_plugin.py`

- [ ] **Step 1: Add summary and persistence roundtrip tests**

```python
def test_summarize_day_status_complete():
    items = [{"duration_hours": 3.75}, {"duration_hours": 3.75}]
    total, percent, delta, status = summarize_day(items, 7.5)
    assert total == 7.5
    assert percent == 100.0
    assert status == "刚好 100%"

def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "data.json"
    data = {"days": {"2026-04-15": {"day_total_hours": 7.5, "items": []}}}
    save_worklog_data(str(path), data)
    loaded, corrupted = load_worklog_data(str(path))
    assert corrupted is False
    assert loaded == data
```

- [ ] **Step 2: Add corrupted file recovery test**

```python
def test_load_corrupted_json_recovers_empty(tmp_path):
    path = tmp_path / "data.json"
    path.write_text("{broken", encoding="utf-8")
    loaded, corrupted = load_worklog_data(str(path))
    assert corrupted is True
    assert loaded == {"days": {}}
```

- [ ] **Step 3: Run the full test file**

Run: `pytest tests/test_worklog_plugin.py -q`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_worklog_plugin.py
git commit -m "test: cover worklog persistence and summaries"
```

### Task 5: Final verification and docs touch-up

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add the new built-in plugin to the README list**

```markdown
4. **🕒 任务工时 (Worklog)**：按天记录多条任务、时间范围、自动换算工时与占比，并实时保存到本地。
```

- [ ] **Step 2: Run targeted verification**

Run: `pytest tests/test_worklog_plugin.py -q`
Expected: PASS

Run: `python -m compileall core plugins tests`
Expected: no syntax errors

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document worklog plugin"
```


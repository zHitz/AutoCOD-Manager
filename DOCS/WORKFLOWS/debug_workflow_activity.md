# Debugging Workflow Activities

This guide outlines the systematic process for debugging workflow activities when they appear to skip or fail silently in the UI Manager, based on a real-world debugging session for the "Train Troops" activity.

## 1. Initial Symptoms
- Activity is configured and appears in the UI list.
- When the bot runs, the activity instantly "skips" and moves to the next one, or fails very quickly without explicit errors in the UI.

## 2. Information Gathering
Before changing code, gather data to form hypotheses:
- **Code Logic:** Check `core_actions.py` to understand what the activity is *supposed* to do.
- **Configurations:** Check the saved JSON config in `data/activity_configs/<group_id>.json` to see what payload is actually being passed to the bot.
- **Execution Logs:** Check the SQLite database (`data/cod_manager.db`) to see actual historical execution statuses (`account_activity_logs`, `task_runs`).

## 3. The Debugging Checklist
Follow these steps to track down the root cause:

### Step A: Verify the Execution Pipeline
Is the activity even reaching the backend executor?
Write a quick mock Python script to test `executor.execute_recipe` with the exact `function_id` and payload. If the mock runs successfully, the pipeline mapping in `executor.py` and `workflow_registry.py` is correct.

### Step B: Check Activity Configurations (JSON)
Look at `data/activity_configs/<group_id>.json`. Pay exceptionally close attention to:
- `enabled`: Must be `true`.
- `cooldown_enabled` and `cooldown_minutes`: If an activity ran successfully recently, the `BotOrchestrator` will automatically skip it if the cooldown hasn't expired. **This is the most common reason for instantaneous skips.**

### Step C: Query the Database Logs
Use a quick SQLite script to check the `account_activity_logs` table:
```python
import sqlite3
con = sqlite3.connect('data/cod_manager.db')
cur = con.cursor()
# Check recent runs for the specific activity
cur.execute("SELECT * FROM account_activity_logs WHERE activity_id = 'your_activity_id' ORDER BY id DESC LIMIT 5")
for row in cur.fetchall():
    print(row)
```
- A status of `SUCCESS` means it ran recently (which triggers the UI cooldowns).
- A status of `FAILED` with an `Unknown execution failure` means the core logic in `core_actions.py` returned `False` or crashed internally without raising a handled API exception.

> [!NOTE]
> **How the UI shows this:** The frontend UI no longer saves `last_run` directly to JSON. Instead, the `GET /api/workflow/activity-config` endpoint queries this SQLite table on the fly and injects `last_run` and `runs_today` into the payload so the frontend config panel can display it.

### Step D: Investigate the Core Logic in `core_actions.py`
If the database shows failures (or if it runs but doesn't do what it should in the game), analyze the target function in `core_actions.py`.
Common pitfalls in `core_actions.py`:
- **Hardcoded Coordinates:** Using static `(X, Y)` screen taps instead of `detector.locate_icon` or `check_activity`. If the player uses a different city layout or device resolution, clicks will hit empty space.
- **Timeouts/Missing Templates:** The detector waits for a screen state (e.g., `wait_for_state`) but the OCR or template matching fails or is outdated, causing the function to time out and return `False` silently.

## Example: Root Cause for "Train Troops" Skipping
In our recent `/debug` case, "Train Troops" was skipping due to two overlapping issues:
1. **The Instant Skip:** The activity had a 10-hour cooldown configured (`"cooldown_minutes": 600`). Because it had successfully completed earlier that day, the backend Orchestrator correctly chose to skip it for the next 10 hours whenever the workflow was run.
2. **The "Silent Failure":** During its first actual runs, it failed internally because it relied on `HOUSE_TAPS = {"archer": (465, 256), ...}`. Since the player's city had buildings in entirely different locations, it tapped the background, didn't find the expected "Train" buttons, and eventually timed out (returning `False`).

## Best Practices to Prevent These Issues
- Always check the `data/cod_manager.db` SQLite logs when an activity's behavior differs between the UI and game. 
- Keep Cooldowns in mind when testing! Temporarily set cooldowns to `0` when actively testing or debugging a new activity.
- Avoid hardcoding absolute `(X, Y)` screen taps for things that move (like city buildings). Use OpenCV template matching or layout-independent methods whenever possible.
- If a function returns `False` in `core_actions.py`, ensure there are `print()` statements right before the `return False` so the execution console logs exactly *why* it decided to fail (e.g., "House button not found").

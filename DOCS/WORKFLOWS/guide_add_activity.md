# Guide: How to Add a New Workflow Activity

When you have a new workflow script or macro you've tested outside the application and want to integrate it as a playable **Activity** in the app, you need to update a few core files. 

The system is designed in a modular way:
1. **Core Actions** (The actual game logic)
2. **Function Registry** (Telling the app about the logic)
3. **Executor Mapping** (Connecting the registry to the real code)
4. **Activity Registry** (Creating the final user-facing task)

Here is the step-by-step guide to adding any new workflow.

---

## Step 1: Write the Core Logic ([core_actions.py](file:///f:/COD_CHECK/UI_MANAGER/backend/core/workflow/core_actions.py))

Every action needs a Python function that executes the ADB commands and checks the screen states.

**File Location:** [backend/core/workflow/core_actions.py](file:///f:/COD_CHECK/UI_MANAGER/backend/core/workflow/core_actions.py)

Add your tested logic as a function here. It should always take `serial` (the emulator ID) and `detector` (the GameStateDetector) as arguments.

**Example:**
```python
def farm_barbarians(serial: str, detector: GameStateDetector) -> bool:
    """Finds and attacks barbarians on the map."""
    print(f"[{serial}] Starting to farm barbarians...")
    
    # 1. Ensure we are in the OUT_CITY lobby
    if not back_to_lobby(serial, detector, target_lobby="IN-GAME LOBBY (OUT_CITY)"):
        return False
        
    # 2. Open search menu
    adb_helper.tap(serial, 42, 422)
    time.sleep(3)
    
    # ... your specific tapping logic ...
    
    # Always return True if successful, False if something broke
    return True
```
*Tip: Always use [wait_for_state](file:///f:/COD_CHECK/UI_MANAGER/backend/core/workflow/core_actions.py#191-258) or `detector.check_activity` to verify the screen state instead of relying purely on blindly tapping and sleeping.*

---

## Step 2: Register the Function ID ([workflow_registry.py](file:///f:/COD_CHECK/UI_MANAGER/backend/core/workflow/workflow_registry.py))

Now the frontend UI needs to know that this function exists so you can add it to recipes. 

**File Location:** [backend/core/workflow/workflow_registry.py](file:///f:/COD_CHECK/UI_MANAGER/backend/core/workflow/workflow_registry.py) -> `FUNCTION_REGISTRY` list

Add a dictionary defining your new function's metadata:

**Example:**
```python
    {
        "id": "nav_to_farm_barbs",               # Unique ID
        "label": "Farm Barbarians",              # Name in UI
        "category": "Core Actions",              # Category in UI
        "icon": "⚔️",                            # Emoji/Icon
        "color": "#6366f1",                      # UI Color
        "description": "Searches for and attacks barbarians",
        "params": [],                            # Add configs here if needed (e.g. level to farm)
    },
```

---

## Step 3: Map the Function in the Executor ([executor.py](file:///f:/COD_CHECK/UI_MANAGER/backend/core/workflow/executor.py))

The Executor receives the `function_id` from the UI and needs to know which real python script to run.

**File Location:** [backend/core/workflow/executor.py](file:///f:/COD_CHECK/UI_MANAGER/backend/core/workflow/executor.py) -> [execute_recipe()](file:///f:/COD_CHECK/UI_MANAGER/backend/core/workflow/executor.py#13-474) loop

Look for the big `if/elif` block containing `# Advanced / State Dependent` mappings and add your function ID there using `asyncio.to_thread`.

**Example:**
```python
            elif fn_id == "nav_to_farm_barbs":
                ok = await asyncio.to_thread(
                    core_actions.farm_barbarians, serial, detector
                )
```
*Note: The string `"nav_to_farm_barbs"` MUST match the [id](file:///f:/COD_CHECK/UI_MANAGER/backend/core/workflow/core_actions.py#290-321) you set in Step 2.*

---

## Step 4: Create the Final User Activity ([workflow_registry.py](file:///f:/COD_CHECK/UI_MANAGER/backend/core/workflow/workflow_registry.py))

If you want this to appear directly in the **"Add Task"** list for users as a standalone Activity, you must register it in the `ACTIVITY_REGISTRY`.

**File Location:** [backend/core/workflow/workflow_registry.py](file:///f:/COD_CHECK/UI_MANAGER/backend/core/workflow/workflow_registry.py) -> `ACTIVITY_REGISTRY` list

Combine your new function with basic startup functions to create a full end-to-end task.

**Example:**
```python
    {
        "id": "farm_barbarians_task",
        "name": "Farm Barbarians",
        "icon": "⚔️",
        "description": "Automatically search and destroy barbarians",
        "steps": [
            {"function_id": "startup_to_lobby", "config": {}}, # Step A: Boot game
            {"function_id": "nav_to_farm_barbs", "config": {}}, # Step B: Run your logic
        ],
        "config_fields": [],
        "defaults": {"cooldown_enabled": True, "cooldown_minutes": 120},
    },
```

---

## Summary Checklist
Whenever you add a new automation:
- [ ] 1. Add logic function `def my_task():` to [core_actions.py](file:///f:/COD_CHECK/UI_MANAGER/backend/core/workflow/core_actions.py)
- [ ] 2. Add metadata block to `FUNCTION_REGISTRY` in [workflow_registry.py](file:///f:/COD_CHECK/UI_MANAGER/backend/core/workflow/workflow_registry.py)
- [ ] 3. Add `elif fn_id == "..."` block to [executor.py](file:///f:/COD_CHECK/UI_MANAGER/backend/core/workflow/executor.py)
- [ ] 4. Add the combined task block to `ACTIVITY_REGISTRY` in [workflow_registry.py](file:///f:/COD_CHECK/UI_MANAGER/backend/core/workflow/workflow_registry.py)

Once these 4 steps are complete, restarting the backend server will immediately make your new activity visible in the application's UI, and the Workflow Executor will know exactly how to run it.

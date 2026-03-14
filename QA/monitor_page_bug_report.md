# Bug Report — Workflow Monitor UI Issues

## 1️⃣ Activity List Not Showing Full Workflow

### Title

Activity list in **Monitor → Activity Detail** does not show the full configured workflow activities.

### Environment

Page: `Workflow → Monitor`
Component: `Activity Detail Panel`
Status: Bot Running

---

### Steps to Reproduce

1. Open **Workflow → Monitor tab**
2. Select an account from **Account Queue**
3. Observe **Activity Detail panel**

---

### Expected Behavior

The Activity Detail panel should show **ALL activities configured in the workflow recipe for the group**, including:

* Completed activities
* Pending activities
* Cooldown activities
* Failed activities

This allows the user to understand:

* which activities **already ran**
* which ones are **pending**
* which ones are **skipped**
* what is the **next activity to execute**

Example:

```
Gather Resource           DONE
Train Troops              DONE
Gather Resource Center    DONE
Catch Pet                 PENDING
Claim Mail                COOLDOWN
Full Scan                 ERROR
```

---

### Actual Behavior

The panel only shows **a partial subset of activities**, for example:

```
Gather Resource
Train Troops
Gather Resource Center
```

Problems caused:

* User **cannot see the full workflow**
* User **cannot determine the next task**
* Impossible to know if an activity was **skipped or not triggered**

---

### Impact

High UX issue.

Monitor page is supposed to show **system intention**, but currently users cannot understand:

* workflow progress
* next activity
* skipped activities

---

### Likely Cause

Frontend likely renders only activities returned from **recent activity logs** instead of using the **full activity configuration for the group**.

Design spec requires:

```
Activity list source =
activity_configs/{group_id}.json
```

and then **merge status per account**.

---

### Expected Fix

Activity Detail should:

1. Load **ALL configured activities** for the group
2. For each activity attach per-account status:

```
enabled
last_run
cooldown_remaining
status
```

Source combination:

```
activity_configs
+
account_activity_logs
```

---

# 2️⃣ Cooldown / Status Data Not Live

### Title

Activity cooldown status in Monitor is not live and does not clear correctly.

---

### Expected Behavior

Cooldown tasks should display:

```
Cooldown 15:32
Cooldown 08:14
Cooldown 00:59
```

And update **every second**.

---

### Actual Behavior

UI shows values like:

```
1/1
177s
22s
43s
```

Problems:

* Format inconsistent with design
* Does not clearly represent cooldown state
* Not obvious if task is **ready or still cooling**

---

### Expected Fix

Cooldown display should follow spec:

```
Status column → "Cooldown"
CD column → countdown timer (MM:SS)
```

Example:

```
Claim Mail     Cooldown     15:23
```

Frontend should run a **1-second timer** updating remaining cooldown.

---

# 3️⃣ Last Run Information Not Updating

### Title

Account queue "Last Run" value always shows **Never** even after account execution.

---

### Expected Behavior

Account rows should show:

```
Last: Just now
Last: 2m ago
Last: 15m ago
```

based on:

```
last_run_times
```

---

### Actual Behavior

UI shows:

```
Never
```

even though the account **has already run today**.

---

### Impact

Users cannot know:

* when an account last executed
* whether cooldown logic is working correctly

---

### Likely Cause

`last_run_times` field not exposed from backend or not used by frontend.

Design spec requires adding to `broadcast_state`:

```
last_run_times
```

---

# 4️⃣ Timeline / Event Log Not Working

### Title

Timeline panel shows **"No events yet"** even while workflow is running.

---

### Expected Behavior

Timeline should display real-time events such as:

```
03:29 Swap done → Buu
03:30 Buu verified
03:31 Queue reorder
03:32 Gohan started activities
```

Data source:

```
WebSocket events:
activity_started
activity_completed
activity_failed
bot_queue_update
```

---

### Actual Behavior

Timeline shows:

```
No events yet
```

even when the workflow is actively executing tasks.

---

### Impact

Users cannot see:

* account swaps
* activity start/finish
* error events

This removes **debugging visibility** for the workflow.

---

# Summary of Issues

| Issue                       | Severity |
| --------------------------- | -------- |
| Activity list incomplete    | High     |
| Cooldown display incorrect  | Medium   |
| Last run not updating       | Medium   |
| Timeline not showing events | Medium   |

---

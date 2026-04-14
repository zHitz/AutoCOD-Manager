# Session Window + Stage Recovery Guide

> Purpose: This document defines the `Session Window + Stage Recovery + Milestone` model used in `TEST/test_alliance_help_v2.py` and explains how to apply the same pattern to future workflows without falling back to naive linear retry.

---

## 1. Why This Pattern Exists

Classic linear workflows fail in game automation because UI state and code step are often out of sync.

Typical failure pattern:

1. Workflow thinks it is at Step 4.
2. Real UI is still at Step 2 because of lag, popup, missed tap, or detector miss.
3. Step 4 fails.
4. Retry repeats Step 4 again on the wrong screen.
5. Workflow either loops or hard-fails.

`Session Window` solves this by adding:

- a bounded recovery window
- explicit stages
- resume logic based on actual current UI
- milestone awareness for irreversible actions
- retry budgets so recovery cannot loop forever

---

## 2. Core Terminology

### Session Window

A temporary execution budget during which the workflow is allowed to self-recover.

Example properties:

- `session_timeout_sec`
- `max_total_transitions`
- `max_root_resets`
- `stage_attempts`

The session can retry, roll back, and resume, but only inside these limits.

### Stage

A recoverable unit of work with its own:

- start condition
- action
- verify condition
- retry budget
- fallback behavior

Examples:

- `S1_ENTER_ALLIANCE`
- `S2_ENTER_HELP_TAB`
- `S3_TAP_HELP`

### Milestone

A committed business action after which the workflow must not go backwards and repeat previous irreversible work.

Examples:

- `help_action_committed`
- `purchase_submitted`
- `dispatch_sent`
- `claim_confirmed`

If a milestone has been committed, recovery must continue forward or clean up, not restart from root.

### Stable Stage

The last stage that fully passed and can be trusted as a resume checkpoint.

Examples:

- `S0_ROOT_BOOTSTRAP` means lobby is known-good
- `S1_ENTER_ALLIANCE` means alliance menu is known-good

### Root Recovery

A hard reset back to a known safe entry point.

Examples:

- back to lobby
- close popup chain
- reopen menu from root context

### In-place Retry

A cheap retry done without leaving the current context.

Examples:

- tap the tab again
- rescan template after a short settle delay
- press back once from profile detail to profile root

---

## 3. Decision Model

The workflow should never ask only:

- "Which step comes next?"

It must always ask:

1. What is the real current UI state?
2. Which stage is already satisfied?
3. Which stage should resume from here?
4. What is the cheapest safe recovery path?
5. Is any milestone already committed?

This changes the execution model from:

`step1 -> step2 -> step3 -> fail`

into:

`detect -> choose stage -> run -> verify -> recover if needed -> continue within budget`

---

## 4. Standard Session Runner Shape

Every reusable session-based workflow should track at least:

```python
session_start_ts
session_timeout_sec
max_total_transitions
max_root_resets

stage_attempts: dict[str, int]
total_transitions: int
root_reset_count: int
milestones_committed: set[str]
current_stage_id: str
last_stable_stage_id: str
timing_stats: dict[str, list[float]]
```

Minimum runner methods:

```python
run()
_check_budget()
_run_stage(stage_spec)
_choose_resume_stage()
_handle_stage_failure(stage_spec, reason)
_recover_to_root(reason)
_recover_to_context(reason)
_cleanup_exit()
```

Recommended stage result contract:

```python
{"ok": True, "message": "..."}
{"ok": False, "error": "..."}
```

### Reusable Test-Only Base Runner

To avoid rewriting the whole engine for every workflow demo, the shared test-only helper now lives at:

- [session_workflow_common.py](/F:/COD_CHECK/UI_MANAGER/TEST/session_workflow_common.py)

This file centralizes the reusable parts of the model:

- `ok() / fail() / is_ok()`
- `human_delay()`
- `make_detector()`
- `save_frame()`
- `print_result_block()`
- `StageSpec`
- `SessionWorkflowRunnerBase`

Meaning:

- the session loop is reusable
- budget handling is reusable
- timing summary is reusable
- stage attempt reset is reusable
- cleanup hook is reusable

What still stays workflow-specific:

- `_choose_resume_stage()`
- `_execute_stage(stage_id)`
- `_handle_stage_failure(...)`
- milestone definitions
- actual tap/detect business logic

So the pattern is now:

1. reuse the shared base runner
2. implement only the stage logic for the target workflow
3. keep everything inside `TEST/` until the model is proven stable

---

## 5. Stage Rules

Each stage should follow this contract:

### Stage input

- current UI may or may not be correct
- stage must validate context before acting

### Stage body

- do the minimum action needed
- avoid large built-in waits unless it is the final fallback

### Stage verify

- confirm expected target or expected retained context
- if action is only a probe, do not over-verify

### Stage failure

- return structured error
- do not silently continue

### Stage success

- update `last_stable_stage_id`
- reset that stage's attempt counter to `0`

Resetting attempts on success is important. Without it, a stage can fail later simply because it was re-entered after a previous pass.

---

## 6. Recovery Levels

Use recovery in this order:

### Level 1: In-place retry

Use when current context is still valid and the action probably just missed.

Examples:

- detector miss
- UI still transitioning
- tab not selected yet
- button not visible yet but parent screen is still correct

Cheap actions:

- tap same control once more
- wait `0.15s - 0.35s`
- rescan current frame

### Level 2: Context recovery

Use when current root is still nearby, but local state drifted.

Examples:

- still inside Alliance, but wrong sub-tab
- in Profile Menu instead of Lobby
- in transition state after opening a sub-menu

Cheap actions:

- single `press_back`
- reopen current menu
- re-enter current parent stage

### Level 3: Root recovery

Use only when workflow is clearly out of expected context.

Examples:

- not in alliance and not in alliance-adjacent states
- popup chain broke current flow
- menu state is unrecoverable
- multiple cheap retries failed

Expensive actions:

- `back_to_lobby_end_workflow()`
- reopen main menu
- restart current workflow path from root checkpoint

---

## 7. Milestone Rules

Milestones are the most important guardrail for non-linear workflows.

### A milestone should be created when:

- the action is business-significant
- the action is not safely repeatable
- repeating it could waste resources or create duplicated behavior

Examples:

- sending troops
- confirming build
- tapping claim on a one-time reward
- starting research
- tapping help if it consumes available help entries

### After a milestone is committed:

- never roll back to stages before it
- only run forward stages
- if cleanup fails, return success with cleanup warning rather than replaying the business action

Example:

```python
if "help_action_committed" in milestones_committed:
    return "S4_EXIT"
```

---

## 8. Budget Design

Every session workflow needs anti-loop protection.

Recommended defaults for light workflows:

```python
session_timeout_sec = 30 to 45
max_total_transitions = 8 to 12
max_root_resets = 1 to 3
max_stage_attempts_default = 2
```

Recommended defaults for navigation-heavy workflows:

```python
session_timeout_sec = 45 to 90
max_total_transitions = 10 to 16
max_root_resets = 2 to 4
```

### Important rule

Use different budgets for:

- cheap local retries
- context recovery
- root recovery

Do not spend root resets on every soft miss.

---

## 9. Resume Strategy

Resume logic is the heart of the model.

Resume should be based on actual screen state, not the previous code branch.

Recommended decision order:

1. If any irreversible milestone is committed, continue only from post-milestone stage.
2. Else if final actionable control is already visible, skip directly to action stage.
3. Else if parent screen is already reached, resume from the child-navigation stage.
4. Else if root context is already valid, resume from first navigation stage.
5. Else do root bootstrap.

Example from `Alliance Help V2`:

```python
if "help_action_committed" in milestones_committed:
    return "S4_EXIT"
if help_button_visible:
    return "S3_TAP_HELP"
if in_alliance:
    return "S2_ENTER_HELP_TAB"
if current_state in LOBBY_STATES:
    return "S1_ENTER_ALLIANCE"
return "S0_ROOT_BOOTSTRAP"
```

This is the exact behavior you want in future workflows too.

---

## 10. Example: Alliance Help V2

The demo in [test_alliance_help_v2.py](/F:/COD_CHECK/UI_MANAGER/TEST/test_alliance_help_v2.py) is the reference implementation.

### Stage map

#### `S0_ROOT_BOOTSTRAP`

Goal:

- reset to known-good lobby root

Action:

- `back_to_lobby_end_workflow()`

Success:

- `IN-GAME LOBBY (IN_CITY)`

Notes:

- not a milestone
- should be cheap and deterministic

#### `S1_ENTER_ALLIANCE`

Goal:

- reach `ALLIANCE_MENU`

Action:

- fast local path:
  - verify lobby
  - ensure lobby menu open
  - tap alliance icon
  - poll quickly
- only on last attempt fallback to production `go_to_alliance()`

Recovery:

- if still in lobby, retry in place
- if in profile or transition, do local back-recovery
- only root-reset if clearly out of context

#### `S2_ENTER_HELP_TAB`

Goal:

- probe into Help tab with minimal cost

Action:

- tap Help tab
- short delay
- if transient, tap once more

Success:

- help button visible, or
- alliance context retained, or
- transient state retained

Important:

- this stage is only a probe
- it should not waste time proving whether help exists

#### `S3_TAP_HELP`

Goal:

- commit the main business action

Action:

- detect help button
- if found, tap it and set milestone
- if not found but still in alliance, classify as `NO_HELP_AVAILABLE`

Milestone:

- `help_action_committed`

#### `S4_EXIT`

Goal:

- cleanly leave workflow

Action:

- fast exit first with `press_back`
- fallback to `back_to_lobby_end_workflow()`

Important:

- if cleanup degrades after milestone, return success with cleanup warning instead of replaying `S3`

---

## 11. Stage Design Template for Other Workflows

Use this template when converting other workflows:

```python
S0_ROOT_BOOTSTRAP
S1_ENTER_PARENT_CONTEXT
S2_ENTER_CHILD_CONTEXT
S3_PREPARE_ACTION
S4_COMMIT_ACTION   # milestone often lives here
S5_VERIFY_POST_ACTION
S6_EXIT
```

Examples:

### Gather RSS Center

- `S0_ROOT_BOOTSTRAP`
- `S1_ENTER_MARKERS_MENU`
- `S2_OPEN_RSS_CENTER`
- `S3_CLASSIFY_BUILD_OR_GATHER`
- `S4_COMMIT_BUILD_OR_DISPATCH`
- `S5_SET_DYNAMIC_COOLDOWN`
- `S6_EXIT`

Milestones:

- `build_dispatch_committed`
- `gather_dispatch_committed`

### Train Troops

- `S0_ROOT_BOOTSTRAP`
- `S1_RESET_POSITION`
- `S2_ENTER_TRAINING_BUILDING`
- `S3_SELECT_TRAIN_OPTION`
- `S4_COMMIT_TRAIN`
- `S5_EXIT`

Milestone:

- `train_confirm_committed`

### Research

- `S0_ROOT_BOOTSTRAP`
- `S1_ENTER_ACADEMY`
- `S2_SELECT_TECH_TREE`
- `S3_SELECT_EMPTY_SLOT`
- `S4_COMMIT_RESEARCH`
- `S5_POST_RESEARCH_HELP`
- `S6_EXIT`

Milestones:

- `research_start_committed`

---

## 12. How to Identify Milestones in New Workflows

Ask these 4 questions:

1. If this action runs twice, can it consume resources twice?
2. If this action runs twice, can it send duplicate command/state to the game?
3. Once this action succeeds, is the UI now logically after a point of no return?
4. Would replaying previous stages after this point be unsafe or wasteful?

If any answer is yes, make it a milestone.

---

## 13. Speed Strategy

Session-based workflows can become slower than production if you over-verify.

Use this speed policy:

### Cheap path first

- short local detection
- short polling
- 1 extra probe
- 1 back navigation if still nearby

### Heavy fallback only last

- full production navigation helper
- full root reset
- long wait-for-state

### Probe stages must stay light

If a stage only exists to move into the next screen, do not make it responsible for proving all downstream semantics.

Example:

- `S2_ENTER_HELP_TAB` should only prove "we are still in the right area"
- `S3_TAP_HELP` should decide "is there actionable help or not"

This split is what keeps the flow fast.

---

## 14. Timing Debug Standard

Every session workflow should emit timing summary so you can see where the real cost is.

Recommended keys:

```python
stage:S0_ROOT_BOOTSTRAP
stage:S1_ENTER_PARENT
stage:S2_ENTER_CHILD
stage:S3_ACTION
stage:S4_EXIT

work:root_bootstrap
work:navigation
work:probe
work:action
work:exit

recovery:root
recovery:context
fallback:production_nav
```

Recommended summary format:

```text
[serial] [TIMING] stage:S2_ENTER_HELP_TAB: count=1 total=0.82s avg=0.82s max=0.82s
```

### How to use timing summary

If a stage is slow:

- reduce fixed sleeps
- split probe and action stages
- avoid repeated full-screen detector calls
- avoid root reset for lobby-adjacent failures

If recovery is slow:

- add cheaper local recovery before root reset
- add better resume logic

---

## 15. Error Model

Use explicit session-specific errors.

Recommended classes:

- `SESSION_TIMEOUT`
- `SESSION_TRANSITION_BUDGET_EXCEEDED`
- `SESSION_ROOT_RESET_EXCEEDED`
- `<STAGE>_FAILED`
- `<ACTION>_NOT_FOUND`
- `<ACTION>_NO_WORK_AVAILABLE`
- `<CLEANUP>_FAILED`

Good examples:

- `S1_ENTER_ALLIANCE_FAILED: Could not reach ALLIANCE_MENU`
- `S3_NO_HELP_AVAILABLE: No help request available`
- `S4_EXIT_CLEANUP_FAILED: Could not return to lobby cleanly`

Avoid vague errors like:

- `Something went wrong`
- `Action failed`
- `Retry failed`

---

## 16. Screenshot Capture Rules

In session-based workflows, capture screenshot on:

- unrecoverable stage failure
- budget exhaustion
- suspicious mismatch before escalation

Do not capture screenshot on every soft miss. That creates noise and slows the loop.

Suggested labels:

- `s1_enter_parent_fail`
- `s2_probe_fail`
- `s3_action_fail`
- `session_timeout_or_budget`

---

## 17. Implementation Checklist for New Workflow

Before converting a workflow, define:

1. Root checkpoint
2. Parent context
3. Child context
4. Business action
5. Milestone point
6. Cleanup path
7. Resume decision order
8. Cheap retries
9. Context recovery path
10. Root recovery path
11. Session budgets
12. Timing keys

If any of these is missing, the workflow is not ready for session-window conversion.

---

## 18. Minimal Version vs Production-Grade Version

### Minimal Version

Use when you want fast adoption for one workflow:

- explicit stages
- resume logic
- one milestone
- root recovery
- transition budget
- timing summary

Good first targets:

- `alliance_help`
- `merchant`
- `claim_mail_reward`

### Production-Grade Version

Use when the pattern is stable and needs to become a reusable framework:

- shared `SessionWorkflowRunner`
- stage spec objects
- reusable recovery policies
- error taxonomy
- shared timing instrumentation
- reusable milestone storage
- stage-specific analytics

Good second-phase targets:

- `research_technology`
- `gather_rss_center`

### Current Practical State In This Repo

Right now the repo already has the first reusable layer in `TEST/`:

- shared base runner:
  - [session_workflow_common.py](/F:/COD_CHECK/UI_MANAGER/TEST/session_workflow_common.py)
- workflow-specific demos:
  - [test_alliance_help_v2.py](/F:/COD_CHECK/UI_MANAGER/TEST/test_alliance_help_v2.py)
  - [test_train_troops_v2.py](/F:/COD_CHECK/UI_MANAGER/TEST/test_train_troops_v2.py)

This is the recommended transition architecture:

- do not push the pattern into production immediately
- prove it first in `TEST/`
- reuse the shared base runner for workflow #2, #3, #4
- only after the pattern is stable, decide whether to move it into production code
- `train_troops`

---

## 19. Recommended Adoption Order

Use this order for future rollout:

1. `alliance_help`
2. `merchant`
3. `claim_mail_reward`
4. `train_troops`
5. `research_technology`
6. `gather_rss_center`
7. `gather_resource`

When adopting, prefer this implementation order:

1. subclass `SessionWorkflowRunnerBase`
2. define stage list
3. define milestone list
4. implement resume logic
5. implement cheap recovery before root reset
6. add timing keys
7. validate in `TEST/` first

Reason:

- start with short workflows
- validate stage model
- validate milestone handling
- validate timing/debug pattern
- then move to multi-branch workflows

---

## 20. Final Practical Rules

If you remember only these rules, the model still works:

1. Never retry a step without checking real current UI.
2. Split probe stages from action stages.
3. Only heavy-reset when cheap local recovery is exhausted.
4. Add milestone as soon as replay becomes unsafe.
5. Resume from actual state, not from previous code path.
6. Reset stage attempt counter after success.
7. Time every stage and recovery path.
8. Do not let probe stages consume the whole session budget.

---

## 21. Reference Files

- Demo implementation: [test_alliance_help_v2.py](/F:/COD_CHECK/UI_MANAGER/TEST/test_alliance_help_v2.py)
- Reusable test-only base runner: [session_workflow_common.py](/F:/COD_CHECK/UI_MANAGER/TEST/session_workflow_common.py)
- Train Troops demo: [test_train_troops_v2.py](/F:/COD_CHECK/UI_MANAGER/TEST/test_train_troops_v2.py)
- Workflow rules: [workflow_dev_rules.md](/F:/COD_CHECK/UI_MANAGER/DOCS/WORKFLOWS/workflow_dev_rules.md)
- Improvement prompt/ideas: [workflow_improve_guide.md](/F:/COD_CHECK/UI_MANAGER/DOCS/WORKFLOWS/workflow_improve_guide.md)
- Test file conventions: [guide_write_test_file.md](/F:/COD_CHECK/UI_MANAGER/DOCS/WORKFLOWS/guide_write_test_file.md)

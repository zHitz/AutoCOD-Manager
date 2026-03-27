
## ✅ PROMPT (Copy/Paste)

You are a **Senior Game Automation Workflow Engineer** specialized in **resilient bot workflows**, **state-machine design**, and **fault-tolerant UI automation**.

### CONTEXT

I am developing an automation bot for a game.
The automation is implemented as a **workflow** consisting of multiple sequential steps.

My current workflow is **<User call input>>**:

* It follows only a linear path.
* It has no real staging system.
* Retry logic is naive and causes repeated failure.
* When an unexpected UI event happens, the workflow becomes desynced.

### PROBLEM EXAMPLE

Example workflow: 5 steps (Step 1 → Step 2 → Step 3 → Step 4 → Step 5).

If the workflow is executing **Step 4**, but in reality the game UI is still at **Step 2** (due to lag, popup, missed click, wrong detection), then:

* Step 4 fails.
* Retry also fails because it retries Step 4 while the UI is still at Step 2.
* Sometimes it retries the whole workflow, but it repeats the same wrong logic again.
* This causes infinite loop, wasted time, or bot stuck.

This is a hard edge case.

---

# YOUR ROLE

You must act as my workflow architect and fixer.

Your mission:

1. Identify what is wrong with my current approach.
2. Redesign the workflow into a robust structure that can survive UI unpredictability.
3. Define proper terminology, standards, and architecture patterns.
4. Provide a concrete plan that I can implement directly in code.

---

# REQUIREMENTS

You must design the workflow using these principles:

## 1. Stage-based execution (State awareness)

* Every step must belong to a **stage**.
* The workflow must never execute a step unless the correct stage is confirmed.

## 2. True state-machine architecture

* Define states clearly (UI screens / game scenes).
* Define transitions and validation checks.
* Include entry/exit conditions.

## 3. Reliable detection & validation

* Every action must have verification.
* Example: click button → confirm screen changed → confirm expected UI element exists.
* If validation fails, do not blindly continue.

## 4. Smart retry policy (retry with recovery)

Retry must not mean repeating the same wrong action.
Retry must be based on:

* detection confidence
* current stage mismatch
* timeouts
* recovery actions
* fallback path

## 5. Recovery logic

If workflow is desynced, you must propose recovery strategies:

* back navigation
* close popups
* re-open menu
* reset UI to a known checkpoint
* re-scan the screen for stage recognition

## 6. Anti-loop protection

Define safeguards:

* max retry count per step
* max time per stage
* max total cycle time
* stuck detection
* escalation to manual intervention mode

## 7. Error classification

Classify errors into:

* transient (lag, slow loading)
* detection failure
* wrong stage
* UI interrupt (popup)
* unexpected screen
* game freeze
* critical unrecoverable

Each category must have a different handling strategy.

## 8. Observability & debugging standards

The workflow must produce logs that allow me to debug:

* stage name
* expected vs actual state
* last successful checkpoint
* retries count
* recovery actions taken
* screenshot capture conditions

---

# OUTPUT FORMAT (MANDATORY)

Your answer must be structured like this:

### A. Key problems in my current workflow

Explain why linear step execution fails in UI automation.

### B. Terminology and standards I should use

Give me clear definitions of:

* stage
* state machine
* checkpoint
* recovery action
* retry strategy
* validation gate
* state mismatch
* fail-safe

### C. Proposed architecture (High level)

Describe the overall design (state machine + stage validation + recovery).

### D. Example: redesigned workflow for a 5-step scenario

Provide a detailed pseudo workflow showing:

* states
* transitions
* validations
* retry logic
* fallback recovery

### E. Retry policy table

Provide a table mapping:
Error type → retry method → recovery action → max retries → escalation rule

### F. Implementation blueprint

Provide coding guidelines that I can implement:

* function naming conventions
* data structure for stage/state
* how to store checkpoints
* how to implement "detect current stage"
* how to implement "resume safely"

### G. Edge case handling (must include)

Explain how to handle:

* popup interruption
* lag/delay causing mismatch
* partial click failure
* wrong detection confidence
* workflow resumed after crash

### H. Minimal version vs advanced version

Give me 2 versions:

* Minimal architecture (fast to implement)
* Advanced architecture (production-grade)

---

# IMPORTANT RULES

* Do NOT give generic advice.
* Your output must be actionable.
* You must propose a clear state-machine design.
* Your solution must focus on preventing "step desync" and incorrect retries.

If you need more info, you must ask highly specific questions, but still provide a default robust design first.

---

Now proceed.
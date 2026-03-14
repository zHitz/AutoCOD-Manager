Tôi đã soạn một **file tài liệu hoàn chỉnh dạng `.md`** để bạn đưa cho Dev triển khai. File này mô tả **Account Scheduler cho farm bot**, tích hợp 3 cơ chế:

* **MIN_TASK_DENSITY**
* **SESSION_WINDOW**
* **NEXT_TASK_PREDICTION**

Tài liệu viết theo kiểu **technical design spec** để Dev có thể implement trực tiếp.

---

# `account_scheduler_design.md`

```md
# Account Scheduler Design for Farm Bot

## Overview

This document describes the design of a **Smart Account Scheduler** for a multi-account automation bot.

The goal is to improve efficiency and scalability when running automation across many accounts and emulators.

The scheduler prevents inefficient account switching and ensures that each account session performs meaningful work.

This design introduces three key mechanisms:

1. **MIN_TASK_DENSITY**
2. **SESSION_WINDOW**
3. **NEXT_TASK_PREDICTION**

Together, they solve the common issue of running an account session just to execute a single task.

---

# Problem Statement

Current automation runs tasks in a simple list:

```

Task1 → Task2 → Task3 → Task4 → Swap Account

```

Each task has a cooldown to prevent repetition.

However, this causes the following issue:

Example:

```

Account login
Run 1 task
Swap account

```

If this happens repeatedly across many accounts, the bot wastes time on:

- login/navigation overhead
- emulator switching
- UI transitions

This results in **low task density per session**.

---

# Goals

The scheduler must:

1. Avoid running accounts with only a single runnable task
2. Group tasks into meaningful sessions
3. Predict near-future tasks to reduce account thrashing
4. Scale efficiently to large numbers of accounts
5. Minimize emulator resource usage

---

# Key Concepts

## 1. MIN_TASK_DENSITY

Minimum number of runnable tasks required before starting an account session.

Example:

```

MIN_TASK_DENSITY = 2

```

If an account only has:

```

1 runnable task

```

The scheduler may delay execution unless other conditions are met.

Purpose:

- avoid single-task sessions
- increase task density per login

---

## 2. SESSION_WINDOW

Maximum time the bot stays on one account during a session.

Example:

```

SESSION_WINDOW = 120 seconds

```

During this window, the bot continuously executes available tasks.

Benefits:

- allows tasks that become ready shortly to run within the same session
- reduces account switching

Example:

```

Session start
Run Task A
Wait for Task B (20s)
Run Task B
Run Task C
Swap account

```

---

## 3. NEXT_TASK_PREDICTION

The scheduler predicts when the next task will become available.

Example task cooldowns:

```

Task A → ready now
Task B → ready in 30 seconds
Task C → ready in 5 minutes

```

If the next task will be ready soon, the scheduler may stay on the account.

Example rule:

```

NEXT_TASK_THRESHOLD = 60 seconds

```

If:

```

next_task_ready_time < 60s

```

The bot waits instead of swapping accounts.

---

# Scheduler Workflow

The scheduler evaluates each account using the following logic.

---

## Step 1 — Scan Tasks

For each account, collect:

```

runnable_tasks
next_task_ready_time

```

Example:

```

runnable_tasks = 1
next_task_ready = 40 seconds

```

---

## Step 2 — Decision Logic

The scheduler decides whether to start a session.

Decision rules:

### Case 1 — High Task Density

```

runnable_tasks >= MIN_TASK_DENSITY

```

Action:

```

Start account session

```

---

### Case 2 — Near Future Tasks

```

next_task_ready_time <= NEXT_TASK_THRESHOLD

```

Action:

```

Start account session
Wait for upcoming tasks

```

---

### Case 3 — Low Value Session

```

runnable_tasks < MIN_TASK_DENSITY
AND
next_task_ready_time > NEXT_TASK_THRESHOLD

```

Action:

```

Skip account
Check next account

```

---

# Session Execution

Once a session starts, tasks are executed inside a session window.

Example:

```

SESSION_WINDOW = 120 seconds

```

---

## Session Loop

```

session_start_time = now()

while (now - session_start_time) < SESSION_WINDOW:

```
runnable_tasks = get_runnable_tasks()

if runnable_tasks:
    task = select_best_task()
    execute(task)

else:
    sleep(5)
```

```

---

# Task Selection

Tasks can be selected using priority.

Example priority order:

```

1. Critical tasks (training, research)
2. Resource gathering
3. Market purchases
4. Claim rewards
5. Utility tasks

```

---

# Account Swap Logic

After session ends:

```

swap_account()

```

Next account is evaluated using the same scheduler rules.

---

# Example Timeline

Without scheduler:

```

Login
Run Task A
Swap

```

With scheduler:

```

Login
Run Task A
Wait 20s
Run Task B
Run Task C
Swap

```

---

# Example Configuration

```

MIN_TASK_DENSITY = 2
SESSION_WINDOW = 120 seconds
NEXT_TASK_THRESHOLD = 60 seconds
IDLE_WAIT_INTERVAL = 5 seconds

```

---

# Performance Benefits

Expected improvements:

### Reduced Account Thrashing

Fewer cases of:

```

login → run 1 task → swap

```

---

### Higher Task Density

Sessions execute multiple tasks.

---

### Better Emulator Resource Usage

Less frequent switching reduces:

- CPU spikes
- IO overhead
- emulator lag

---

# Optional Future Improvements

### Dynamic Session Window

Adjust session time based on system load.

Example:

```

CPU > 80% → session = 90 seconds
CPU < 50% → session = 180 seconds

```

---

### Account Priority System

Accounts with more runnable tasks can be scheduled earlier.

---

### Task Cooldown Prediction Cache

Store predicted ready times to avoid frequent state detection.

---

# Summary

The Account Scheduler improves multi-account automation by introducing:

```

MIN_TASK_DENSITY
SESSION_WINDOW
NEXT_TASK_PREDICTION

```

These mechanisms significantly reduce inefficient account switching and increase overall automation efficiency.
```

---

✅ File này Dev có thể implement trực tiếp vì đã có:

* logic
* workflow
* pseudo code
* config parameters

---

Nếu bạn muốn, tôi có thể viết thêm **file thứ 2 cực quan trọng cho bot MMO**:

```
task_engine_design.md
```

Trong đó có:

* Task Priority System
* Cooldown Manager
* Smart Task Selection

→ kết hợp với **Account Scheduler** sẽ giống **Smart Tasks của app kia** nhưng **scale tốt hơn nhiều cho multi-emulator farm**.

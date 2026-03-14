# Smart Wait Design Notes

## Current Implementation: Option A — Blocking Wait

When an account is on cooldown but its remaining time is within the `swap_wait_threshold_min` window, the orchestrator **blocks the entire loop** and waits for the cooldown to expire before processing that account.

### Behavior
- Orchestrator pauses at the currently-active account
- No other emulators or accounts are processed during the wait
- After wait completes, the account runs normally (no swap needed)

### Tradeoffs
- ✅ Avoids unnecessary swap (saves ~1 min per avoided swap)
- ❌ Blocks other emulators that might be ready to run

### Config
- `swap_wait_threshold_min` in Misc settings (default: 5 minutes)
- Set to 0 to disable Smart Wait entirely

---

## Future Option B — Skip to Next Ready Emu (NOT IMPLEMENTED)

Instead of blocking, skip the cooldown account and process other ready emulators first. Come back to the cooldown account when it's ready.

### How it would work
1. Account X on Emu 4 is on cooldown (3 min remaining)
2. Instead of waiting 3 min → skip to Emu 5 / Emu 6 if they have ready accounts
3. After processing other emus → check if Emu 4's account is now ready
4. If ready → process. If still on cooldown → skip again or wait

### Complexity
- Requires queue restructuring to support "deferred" accounts
- Must handle cross-emu swap cost (is swapping to Emu 5 worth 2 min to save waiting 3 min?)
- Need to track per-emu "revisit" state
- Risk of infinite deferral if all accounts keep ending up on cooldown

### When to implement
When there are 4+ emulators with staggered cooldowns and the blocking wait is causing noticeable throughput loss.

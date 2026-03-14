# Workflow Bot — KPI Checklist

> Dùng để đánh giá hiệu suất và sức khỏe hệ thống sau mỗi phiên chạy bot.
> Data source: `account_activity_logs`, `swap_*.jsonl`, `smart_queue/`, `broadcast_state`.

---

## 1. Account Coverage (Độ phủ account)

| KPI | Công thức | Target | Ý nghĩa |
|-----|-----------|--------|---------|
| **% Account đạt min_runs** | `accounts_met_target / total_accounts × 100` | ≥ 90% | Bao nhiêu % account trong group đã chạy đủ số lần tối thiểu/ngày |
| **Accounts chưa chạy lần nào** | `COUNT(accounts WHERE runs_today = 0)` | 0 | Phát hiện account bị "bỏ quên" do swap loop hoặc lỗi |
| **Runs/account/day** (median) | `MEDIAN(runs_today per account)` | ≥ 3 | Số lần trung bình mỗi account được chạy trong ngày |
| **Runs/account/day** (min–max spread) | `MAX(runs) - MIN(runs)` | ≤ 2 | Chênh lệch quá lớn = unfair distribution |

### Fairness Index
```
fairness = 1 - (σ / μ)
```
- `σ` = standard deviation of runs_today across accounts
- `μ` = mean runs_today
- **Target**: ≥ 0.85 (1.0 = hoàn hảo, mọi account chạy đều)
- **Cảnh báo**: < 0.7 → có account bị thiên vị hoặc bỏ sót

---

## 2. Activity Completion (Hiệu suất thực thi)

| KPI | Công thức | Target | Ý nghĩa |
|-----|-----------|--------|---------|
| **Activity success rate** | `SUCCESS / (SUCCESS + ERROR) × 100` | ≥ 95% | % activity chạy thành công (per group, per day) |
| **Activity skip rate** | `SKIPPED / total_executions × 100` | ≤ 10% | % activity bị skip do cooldown hoặc lỗi |
| **Error rate per activity** | `ERROR count per activity_id` | ≤ 5% mỗi activity | Activity nào lỗi nhiều nhất → cần fix script |
| **Avg activity duration** | `AVG(duration_ms) per activity_id` | — | Baseline để phát hiện anomaly (chạy quá lâu hoặc quá nhanh) |

### Per-Activity Breakdown
```
Activity               Success   Error   Skipped   Avg Duration
────────────────────────────────────────────────────────────────
Gather Resource Center    48        2        5        12.3s
Catch Pet                 45        0       10         8.7s
Claim Mail                50        0        5         3.2s
Train Troops              47        3        5        15.1s
Full Scan                 40        8        7        45.6s  ⚠️
```

---

## 3. Swap Efficiency (Hiệu suất swap)

| KPI | Công thức | Target | Ý nghĩa |
|-----|-----------|--------|---------|
| **Swap success rate** | `verified_match / total_swap_attempts × 100` | ≥ 95% | % swap thành công từ lần thử đầu |
| **Avg swap attempts** | `AVG(attempts per swap)` | ≤ 1.2 | Gần 1 = swap ổn, > 2 = có vấn đề OCR/template |
| **% Swap mất > 3 phút** | `COUNT(swap_duration > 180s) / total_swaps × 100` | ≤ 5% | Swap chậm = game lag, OCR fail, hoặc emu chưa boot |
| **Unnecessary swap count** | `COUNT(swap WHERE previous_account = target_account)` | 0 | Swap không cần thiết (swap đi rồi swap lại cùng account) |
| **Smart Wait trigger rate** | `smart_wait_count / total_cooldown_checks × 100` | — | Bao nhiêu lần Smart Wait thực sự tránh được swap thừa |
| **Smart Wait saved time** | `SUM(avoided_swap_duration_estimate)` | — | Ước tính thời gian tiết kiệm nhờ không swap |

### Swap Duration Histogram
```
< 30s    ████████████████████ 72%  ✅ Tốt
30-60s   ████████ 18%              OK
60-180s  ███ 7%                    ⚠️ Chậm
> 180s   █ 3%                      🔴 Cần kiểm tra
```

---

## 4. Time Utilization (Sử dụng thời gian)

| KPI | Công thức | Target | Ý nghĩa |
|-----|-----------|--------|---------|
| **Median wait time giữa 2 lần chạy/account** | `MEDIAN(gap between consecutive runs per account)` | ≤ cooldown_min + 5m | Đợi quá lâu = hệ thống bận swap hoặc chạy account khác |
| **% Thời gian idle** | `idle_time / total_runtime × 100` | ≤ 15% | Hệ thống đang chờ (cooldown, Smart Wait) quá nhiều |
| **% Thời gian swap** | `total_swap_time / total_runtime × 100` | ≤ 20% | Quá nhiều thời gian dùng cho swap = cần tối ưu queue |
| **% Thời gian execute** | `total_execution_time / total_runtime × 100` | ≥ 65% | Thời gian thực sự chạy activity — con số quan trọng nhất |
| **Cycles completed/hour** | `total_cycles / runtime_hours` | ≥ 1 | Bao nhiêu vòng queue hoàn thành mỗi giờ |

### Time Breakdown Chart
```
Total runtime: 6h 24m
├── 🟢 Executing activities:  4h 10m (65%)
├── 🔄 Swapping accounts:     0h 52m (14%)
├── ⏳ Cooldown waiting:       1h 05m (17%)
└── ⚪ System overhead:        0h 17m  (4%)
```

---

## 5. Emulator Health (Sức khỏe emulator)

| KPI | Công thức | Target | Ý nghĩa |
|-----|-----------|--------|---------|
| **Emu crash count** | `COUNT(emu_restart or emu_offline events)` | 0 | Emulator bị crash → mất thời gian restart |
| **Emu boot time** | `AVG(time from start to first account ready)` | ≤ 60s | Boot quá lâu = emu lag hoặc game update |
| **Cross-emu swap count** | `COUNT(swap between different emulators)` | Minimize | Cross-emu swap tốn thời gian hơn in-game swap |
| **Accounts per emulator** | `COUNT(accounts) per emu_index` | ≤ 3 | Quá nhiều account/emu → swap loop nhiều |

---

## 6. Queue Intelligence (Chất lượng thuật toán)

| KPI | Công thức | Target | Ý nghĩa |
|-----|-----------|--------|---------|
| **Early probe hit rate** | `COUNT(probe matched active) / COUNT(probe attempts) × 100` | ≥ 80% | Probe đúng account đang active → tránh swap đầu |
| **Reorder effectiveness** | `COUNT(reorder avoided swap) / COUNT(reorder triggered) × 100` | ≥ 70% | Queue reorder thực sự giúp tránh swap hay không |
| **Ping-pong swap count** | `COUNT(A→B→A on same emu within 10 min)` | 0 | Dấu hiệu chính của bug Smart Wait không hoạt động |

---

## 7. Scoring Summary

| Grade | Score | Điều kiện |
|-------|-------|-----------|
| 🟢 **A** | 90-100 | Coverage ≥95%, Success ≥95%, Execute time ≥70%, No ping-pong |
| 🟡 **B** | 70-89 | Coverage ≥85%, Success ≥90%, Execute time ≥60% |
| 🔴 **C** | <70 | Dưới ngưỡng B, cần review config hoặc fix bug |

### Công thức tổng hợp
```
Score = (Coverage×25 + SuccessRate×25 + ExecuteTime%×20 + SwapEfficiency×15 + Fairness×15) / 100
```

---

## 8. Data Sources

| Metric Group | Primary Source | File/Table |
|-------------|---------------|------------|
| Account Coverage | DB | `account_activity_logs` |
| Activity Completion | DB | `account_activity_logs` |
| Swap Efficiency | Log | `logs/swap_account/swap_YYYY-MM-DD.jsonl` |
| Smart Wait | Log | `logs/smart_queue/*.jsonl` |
| Time Utilization | Computed | `broadcast_state` timestamps + log timestamps |
| Emulator Health | Log | `swap_*.jsonl` (boot/crash events) |
| Queue Intelligence | Log | `swap_*.jsonl` (reorder/probe events) |

### Phase 1 — Tích hợp vào Monitor Tab (đang plan)
Thêm 1 section **KPI Summary** nhỏ ở top của Monitor tab (cái đang design), hiển thị 4-5 metrics quan trọng nhất real-time:

| Metric | Lý do ưu tiên | Data đã có sẵn |
|--------|---------------|-----------------|
| **Fairness Index** | Phát hiện unfair ngay | ✅ [broadcast_state](cci:1://file:///f:/COD_CHECK/UI_MANAGER/backend/core/workflow/bot_orchestrator.py:104:4-135:54) → runs per account |
| **Activity Success Rate** | Biết ngay script nào lỗi | ✅ `account_activity_logs` |
| **Ping-pong Swap Count** | Validate Smart Wait đúng | ✅ `swap_*.jsonl` |
| **% Execute Time** | Metric quan trọng nhất | ⚠️ Cần tính từ timestamps |
| **Current Cycle / Coverage** | Đã chạy bao nhiêu % | ✅ [broadcast_state](cci:1://file:///f:/COD_CHECK/UI_MANAGER/backend/core/workflow/bot_orchestrator.py:104:4-135:54) |

→ Chỉ cần thêm ~1 API endpoint + 1 small panel, **không cần page riêng**.

### Phase 2 — Standalone KPI Page (sau này)
Khi data nhiều hơn (chạy vài tuần), làm page riêng `/kpi` với:
- Lịch sử KPI theo ngày (line chart)
- Per-group comparison
- Auto-grade A/B/C
- Export report

### Tôi recommend:
> **Phase 1 trước** — gắn vào Monitor tab luôn vì dùng chung data source. Phase 2 làm khi bạn cần metrics historical.

Bạn muốn tôi:
1. **Bổ sung KPI panel vào design spec của Monitor tab** (Phase 1)?
2. Hay **tạo riêng 1 design spec cho full KPI page** (Phase 2)?
3. Hay cả 2?
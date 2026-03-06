1) Đánh giá nhanh hiện trạng (để chốt điểm xuất phát)
Hiện app đã có nhiều mảnh tốt:

Có activity registry làm source-of-truth từ backend (/api/workflow/activity-registry).

Có workflow activity config theo group (/api/workflow/activity-config/{group_id}) để lưu cấu hình chạy bot theo group/account set.

Task page đang build dữ liệu từ /api/accounts + /api/tasks/history, rồi tự suy luận check/status ở frontend.

DB hiện có task_runs + task_run_steps + accounts + scan_snapshots, đủ để chạy được nhưng chưa tối ưu cho “Task checklist theo account x activity” chuẩn production lâu dài.

2) Kết luận kiến trúc: nên có bảng fact riêng cho Task page
Bạn đưa account_activity_logs là đúng hướng.
Để dùng lâu dài, mình đề xuất nâng thành v2 (đủ cho analytics, roadmap, audit, retry, SLA):

2.1 Bảng chính (fact table)
CREATE TABLE IF NOT EXISTS account_activity_logs (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id            TEXT NOT NULL,                -- link task_runs.run_id
    account_id        INTEGER NOT NULL,             -- link accounts.id
    game_id           TEXT NOT NULL,                -- denormalized for fast query/UI
    emulator_id       INTEGER,                      -- link emulators.id
    group_id          INTEGER,                      -- account group at execution time
    activity_id       TEXT NOT NULL,                -- stable key (registry id)
    activity_name     TEXT NOT NULL,                -- display snapshot
    status            TEXT NOT NULL,                -- PENDING/RUNNING/SUCCESS/FAILED/SKIPPED/CANCELED
    error_code        TEXT DEFAULT '',
    error_message     TEXT DEFAULT '',
    started_at        TEXT NOT NULL,
    finished_at       TEXT,
    duration_ms       INTEGER DEFAULT 0,
    attempts          INTEGER DEFAULT 1,
    source            TEXT DEFAULT 'workflow',      -- workflow/manual/scheduler/retry
    metadata_json     TEXT DEFAULT '{}',            -- inputs/options/context
    result_json       TEXT DEFAULT '{}'             -- structured output for Task page
);
2.2 Index bắt buộc
CREATE INDEX IF NOT EXISTS idx_aal_game_started
ON account_activity_logs(game_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_aal_account_started
ON account_activity_logs(account_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_aal_activity_started
ON account_activity_logs(activity_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_aal_status_started
ON account_activity_logs(status, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_aal_run
ON account_activity_logs(run_id);
2.3 Ràng buộc/consistency
status nên có check constraint enum.

finished_at >= started_at (nếu có trigger thì tốt).

activity_id phải là key từ activity registry (không chỉ activity_name text tự do).

3) Luồng dữ liệu chuẩn cho team Workflow
3.1 Khi bot bắt đầu activity
Insert PENDING/RUNNING vào account_activity_logs.

3.2 Khi activity xong
Update record đó:

status

finished_at

duration_ms

error_*

result_json (nếu có số liệu).

3.3 Khi fail/retry
Tăng attempts

Ghi thêm bản ghi mới hoặc append strategy (mình khuyên new row mỗi attempt cho audit sạch).

4) API contract dài hạn cho Task page
Đừng để Task page tự “suy luận chắp vá” từ nhiều endpoint như hiện tại.
Nên có API chuyên biệt:

4.1 GET /api/task/checklist?date=YYYY-MM-DD&group_id=&status=&priority=&q=
Trả về:

accounts[] đã flatten sẵn

mỗi account có activities[] theo selected template

stats tổng hợp (coverage, overdue, at_risk, ...)

4.2 POST /api/task/checklist/template
Lưu template selected activities (theo scope: org/user/group).

4.3 POST /api/task/checklist/mark
Mark done/undo cho account + activity (manual override).

=> Frontend Task page sẽ chỉ render, không cần tự map quá nhiều như hiện tại.

5) Về “Settings chọn Activity để Task page hiện”
Hiện bạn đang lưu selection ở localStorage Settings và Task đọc lại localStorage. Cách này chạy nhanh nhưng không ổn enterprise/multi-user:

Không sync giữa máy khác

Không có version/audit

Không có scope theo user/group/team

Settings đang fetch registry và lưu local selection localStorage.
Task đang đọc selection từ localStorage để đổi checklist templates.

Đề xuất nâng cấp
Tạo table task_templates và task_template_items.

Scope: org_default, user_id, group_id.

Có updated_by, updated_at, version.

Settings gọi API save/load template thay vì localStorage.

6) Chuẩn hóa trạng thái/ưu tiên (business rules)
Task page hiện đang derive status ở frontend (overdue/at-risk/on-track).
Long-term nên chuyển về backend rule engine:

Rule configable theo activity SLA (VD full_scan quá 24h = overdue)

Rule theo priority weight của activity

Rule theo account tier/group

Nên thêm:

activity_sla_hours

activity_weight

critical (already concept in template, formalize in DB)

7) Roadmap triển khai (để gửi team Workflow)
Phase 1 (1-2 sprint): nền dữ liệu
Tạo account_activity_logs v2 + index + migration.

Hook lifecycle log vào workflow executor.

Emit ws event chuẩn (activity_started, activity_completed, activity_failed).

Phase 2 (1 sprint): API chuyên dụng Task
GET /api/task/checklist aggregate từ logs + account snapshot.

POST /api/task/checklist/mark.

GET/POST template persistence server-side.

Phase 3 (1 sprint): frontend cleanup
Task page bỏ derive phức tạp frontend.

Settings bỏ localStorage, dùng API template.

Add filters/sort/export đúng business.

Phase 4 (roadmap xa): reliability & analytics
Materialized daily summary table.

SLA dashboard.

Retry policy + reason taxonomy (error_code).

Audit trail và timeline per account/activity.

8) Trả lời trực diện câu của bạn: “đề xuất full, dư roadmap”
Mình chốt:

Bảng bạn nhận là nền tốt, nhưng muốn dùng lâu dài cho Task page thì nên nâng theo bản v2 ở trên (thêm game_id, activity_id, metadata/result, index, scope/template server-side).

Làm theo roadmap 4 phase thì team Workflow implement dần được, không phá code đang chạy.

Commands mình đã dùng để phân tích
rg -n "activity-registry|activity-config|workflow" backend/api.py frontend/js/pages/workflow.js frontend/js/pages/task.js frontend/js/pages/settings.js backend/storage/database.py | head -n 120

nl -ba backend/api.py | sed -n '834,1165p'

nl -ba backend/storage/database.py | sed -n '1186,1260p'

nl -ba frontend/js/pages/settings.js | sed -n '160,380p'

nl -ba frontend/js/pages/task.js | sed -n '70,240p'

nl -ba frontend/js/pages/workflow.js | sed -n '720,780p'
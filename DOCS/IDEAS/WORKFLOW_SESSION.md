Ý tưởng này rất đúng hướng, và thực ra hợp với workflow engine hiện tại hơn là chỉ vá riêng từng function.

Mình gọi nó là:

**`Session Window + Stage Recovery`**

Nó là một lớp điều phối nhỏ bọc quanh workflow function, để workflow không còn chạy kiểu:
- làm bước 1
- fail
- trả lỗi luôn

mà chuyển thành:
- mở một `session window`
- chia workflow thành các `stage`
- mỗi stage có `entry condition`, `action`, `success condition`, `fallback`
- trong session đó được phép retry, rollback mềm, resume từ milestone
- nhưng có `budget` rõ để không loop vô tận

---

**1. Mental model**

Với `Alliance Help`, có thể chia như này:

- `S0_BOOTSTRAP`
  - đảm bảo app sống, về lobby phù hợp
- `S1_ENTER_ALLIANCE`
  - mục tiêu: vào `ALLIANCE_MENU`
- `S2_ENTER_HELP_TAB`
  - mục tiêu: đang ở đúng màn/tab help
- `S3_TAP_HELP`
  - milestone hành động chính: đã bấm help
- `S4_EXIT`
  - quay về lobby sạch

Quan trọng là mỗi stage không chỉ có “do action”, mà có thêm:

- `can_start_if`
- `is_already_satisfied`
- `perform`
- `verify`
- `fallback`
- `retry_limit`
- `rollback_scope`

---

**2. Session Window là gì**

Một `session window` là khoảng thời gian workflow được quyền tự phục hồi.

Ví dụ:

```python
session = WorkflowSession(
    workflow_id="alliance_help",
    serial=serial,
    max_duration_sec=45,
    max_total_attempts=8,
    max_same_stage_retries=3,
)
```

Trong window này:
- được retry stage
- được quay lui về stage trước
- được restart nhánh navigation
- nhưng không vượt budget

Nếu hết budget:
- fail có cấu trúc
- log rõ fail ở stage nào
- snapshot stage cuối

---

**3. Stage vs Milestone**

Đây là phần quan trọng nhất trong ý tưởng của bạn.

**Stage**
- là một bước có thể thử lại
- ví dụ: `enter_alliance`, `enter_help_tab`

**Milestone**
- là một điểm cam kết trạng thái workflow
- sau milestone, không nên quay lại trước đó nếu action đó không idempotent hoặc không thể làm lại

Ví dụ:

`A -> B -> C`

Nếu `A` là hành động chỉ làm được một lần:
- khi `A` xong, mark `milestone_A_done = True`
- nếu lỗi ở `B`, workflow không được quay lại chạy lại `A`
- recovery phải resume từ `B` hoặc tìm đường xác minh lại trạng thái sau `A`

Nói cách khác:

- `stage` = đơn vị điều hướng
- `milestone` = đơn vị commit nghiệp vụ

---

**4. Rule resume theo ý bạn**

Ví dụ `Alliance Help`:

- nếu **chưa bấm help** và **không ở alliance**
  - được quay lại `S1_ENTER_ALLIANCE`
  - coi như restart phần đầu workflow
- nếu **chưa bấm help** nhưng **vẫn đang ở alliance**
  - không cần chạy lại từ đầu
  - chỉ resume từ `S2_ENTER_HELP_TAB`
- nếu **đã bấm help**
  - coi như milestone hoàn thành nghiệp vụ chính
  - lỗi sau đó chỉ cần cleanup/exit
  - không quay lại bấm help lần nữa trừ khi explicitly xác nhận chưa commit

Đây chính là thứ linear workflow hiện tại đang thiếu.

---

**5. Cấu trúc state machine đề xuất**

Mỗi workflow có thể khai báo kiểu này:

```python
stages = [
    Stage(
        id="enter_alliance",
        entry_check=is_in_or_can_reach_alliance_context,
        success_check=is_alliance_menu,
        action=go_to_alliance_action,
        fallback=back_to_lobby_fallback,
        retry_limit=2,
    ),
    Stage(
        id="enter_help_tab",
        success_check=is_help_tab_open,
        action=open_help_tab_action,
        fallback=recover_to_alliance_menu,
        retry_limit=2,
    ),
    Stage(
        id="tap_help",
        success_check=is_help_consumed_or_no_more_help,
        action=tap_help_action,
        fallback=recheck_help_state,
        retry_limit=2,
        milestone=True,
    ),
    Stage(
        id="exit",
        success_check=is_back_to_lobby,
        action=exit_alliance_action,
        fallback=back_to_lobby_fallback,
        retry_limit=2,
    ),
]
```

Session runner sẽ:
1. check stage hiện tại đã satisfied chưa
2. nếu rồi thì skip qua stage tiếp
3. nếu chưa thì action
4. verify
5. fail thì fallback
6. retry trong budget
7. nếu vượt limit thì rollback về stage phù hợp

---

**6. Recovery policy nên có 3 mức**

Mình khuyên chuẩn hóa 3 mức recovery:

**Level 1: Retry same stage**
- UI chậm
- detector miss
- tap chưa ăn

Ví dụ:
- đang ở alliance rồi nhưng chưa detect nút help
- retry scan/tab open lại

**Level 2: Rollback to previous stable stage**
- lệch màn hình nhưng app vẫn healthy

Ví dụ:
- mục tiêu là help tab nhưng lại đang ở alliance main
- rollback về `S1_ENTER_ALLIANCE` stable state rồi làm lại `S2`

**Level 3: Reset to workflow root**
- state hỗn loạn / unknown / popup / desync

Ví dụ:
- khỏi alliance hẳn
- rơi sang city screen
- popup lạ
- network issue recovered xong UI lệch

Thì quay về `S0_BOOTSTRAP`

---

**7. Để tránh loop vô tận**

Đây là bắt buộc. Mình đề xuất mỗi session có 4 loại budget:

- `max_duration_sec`
- `max_total_transitions`
- `max_stage_attempts[stage_id]`
- `max_root_resets`

Ví dụ cho `Alliance Help`:
- max duration: `45s`
- max transitions: `10`
- max retry mỗi stage: `2`
- max reset về root: `2`

Nếu vượt:
- fail với code kiểu:
  - `SESSION_STAGE_BUDGET_EXCEEDED`
  - `SESSION_ROOT_RESET_EXCEEDED`
  - `SESSION_TIMEOUT`

---

**8. Alliance Help là demo rất đẹp**

Vì nó có đủ tình huống để chứng minh model này:

**Case 1**
- chưa vào alliance
- tap icon miss
- vẫn ở city
- session rollback về `enter_alliance`

**Case 2**
- đã vào alliance
- tap help tab miss
- vẫn ở alliance menu
- session chỉ retry `enter_help_tab`

**Case 3**
- đã vào help tab
- detector miss nút help 1 frame
- session retry scan thay vì fail `nothing to help`

**Case 4**
- đã tap help
- sau đó popup/animation khiến verify lệch
- vì `tap_help` là milestone nghiệp vụ
- workflow không quay lại từ đầu, chỉ cleanup rồi finish

---

**9. Với workflow có milestone không được chạy lại**

Ví dụ `A -> B -> C`, trong đó `A` không được lặp lại:

Ta cần thêm metadata:

```python
Milestone(
    id="A_done",
    irreversible=True,
    detect_committed=is_A_committed,
)
```

Khi workflow recover:
- nếu `A_done = True`
- runner không bao giờ gọi lại action `A`
- nếu cần thì chỉ:
  - xác minh vẫn đang sau A
  - rồi resume B

Cái hay là milestone có thể được set bằng 2 cách:
- action trả `committed=True`
- hoặc detect từ UI/state rằng A đã xảy ra

---

**10. Kiến trúc thực dụng để cắm vào code hiện tại**

Mình không nghĩ nên rewrite toàn engine ngay. Nên làm theo 2 lớp:

**Lớp 1: helper session runner trong `core_actions.py`**
- dùng cho 1 vài workflow demo trước
- ví dụ:
  - `run_session_window(serial, detector, session_def)`

**Lớp 2: áp dụng cho workflow cụ thể**
- đầu tiên là `alliance_help`
- sau đó nếu ổn thì mới áp vào:
  - `research_technology`
  - `gather_rss_center`
  - `train_troops`

Tức là không cần sửa registry/executor nhiều ngay từ đầu.

---

**11. Output/logging nên có**

Muốn demo đẹp thì log phải rất rõ:

```text
[emulator-5580] [SESSION] Start alliance_help window (45s)
[emulator-5580] [STAGE] enter_alliance attempt 1
[emulator-5580] [STAGE] enter_alliance failed verify -> rollback root
[emulator-5580] [STAGE] enter_alliance attempt 2
[emulator-5580] [STAGE] enter_alliance success
[emulator-5580] [STAGE] enter_help_tab attempt 1
[emulator-5580] [STAGE] enter_help_tab desynced -> retry in-place
[emulator-5580] [STAGE] tap_help success -> milestone committed
[emulator-5580] [SESSION] Completed
```

History Logs tab sẽ rất hợp với cơ chế này.

---

**12. Kết luận**

Ý tưởng của bạn rất mạnh, và theo mình nên định nghĩa nó như sau:

- `Session Window` = khoảng thời gian workflow được phép tự phục hồi
- `Stage` = từng bước điều hướng có verify/fallback
- `Milestone` = điểm commit nghiệp vụ để biết resume từ đâu
- `Recovery Budget` = giới hạn để không loop vô tận

Nếu làm demo, `Alliance Help` là ứng viên số 1 vì:
- ngắn
- dễ chia stage
- dễ tạo fail path
- dễ nhìn thấy hiệu quả so với linear flow hiện tại

Nếu bạn muốn, bước tiếp theo mình có thể làm luôn:
1. thiết kế spec cực cụ thể cho `Alliance Help Session Window v1`
2. hoặc code thẳng bản demo `alliance_help_v2()` theo model này.
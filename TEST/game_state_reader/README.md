# PET SANCTUARY True-Parameter Reader

Research-first project trong `TEST/game_state_reader` de tra loi cau hoi:

`Game screen PET SANCTUARY co expose du source runtime that su de doc pet_token ma khong can OCR hay doc screenshot khong?`

## Goals
- Di toi man `PET SANCTUARY` bang navigation hien co.
- Lay `uiautomator dump` tu emulator.
- Parse XML dump de xac nhan hierarchy co expose du lieu that hay khong.
- Neu hierarchy cua Unity khong expose text, chuyen sang `runtime_log_probe`:
  - doc `park/log` ma app tu ghi
  - doc `logcat` cua process game
  - doc cac file save/cache theo `roleId` trong `GLGData/.../doc`
  - tim `pet_token` tu key/value that trong JSON payload hoac local save
- Khong bao gio dung OCR trong project nay.
- Khong doc screenshot de suy luan token.

## Current Scope
- Man muc tieu: `PET SANCTUARY`
- Chi so dau tien: `pet_token`
- Data source uu tien: `ADB + UI hierarchy dump`
- Neu hierarchy khong co du lieu, chi duoc dung runtime-accessible source that:
  - `park/log`
  - role-scoped local save/cache files
- Trang thai: spike/research, chua thay the pipeline scan hien tai

## Expected Output
Runner se ghi `result.json` trong thu muc artifact theo tung lan chay:

```json
{
  "ok": true,
  "method": "uiautomator_dump",
  "screen": "PET_SANCTUARY",
  "pet_token": 12345,
  "evidence": {
    "xml_path": "F:/.../window_dump.xml",
    "screenshot_path": "F:/.../screen.png",
    "parsed_path": "F:/.../parsed.json"
  },
  "error": null
}
```

Neu hierarchy dump khong usable, project phai tra ve chan doan ro rang nhu:
- `NAV_TARGET_NOT_REACHED`
- `HIERARCHY_DUMP_FAILED`
- `PET_SANCTUARY_NOT_CONFIRMED`
- `PET_TOKEN_NOT_FOUND`
- `UNSUPPORTED_RENDER_SURFACE`
- `RUNTIME_LOG_NOT_ACCESSIBLE`
- `TRUE_PARAMETER_SOURCE_NOT_FOUND`

## Detection Order
1. `uiautomator dump`
2. Neu dump chi thay `unitySurfaceView` hoac khong expose token, chuyen sang `runtime_log_probe`
3. Runtime probe se thu:
   - latest `park/log/<date>`
   - recent `logcat`
   - endpoint JSON trong `JsonResponse: parseData v2 = ...`
   - local save/cache file theo `roleId`

## How To Run
Chay runner cho 1 emulator:

```bash
python TEST/game_state_reader/runner.py --serial emulator-5556
```

Neu can chup screenshot lam evidence thu cong, bat minh hoc:

```bash
python TEST/game_state_reader/runner.py --serial emulator-5556 --capture-screenshot
```

Tuy chon custom artifact root:

```bash
python TEST/game_state_reader/runner.py --serial emulator-5556 --output-dir TEST/game_state_reader/artifacts
```

## Notes
- V1 co reuse `go_to_pet_sanctuary()` de toi dung man can nghien cuu.
- Screenshot khong duoc dung de doc chi so.
- Neu hierarchy dump co du du lieu, phase sau moi tinh chuyen dong goi thanh reusable checker.
- Neu runtime probe tim thay source that, project se uu tien reader nay thay vi bat ky cach suy luan tren anh nao.

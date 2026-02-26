# COD Game Automation Manager

Desktop application for managing LDPlayer emulators, running macro scripts, and performing OCR-based scans on game accounts.

**Stack:** FastAPI (backend) + Vanilla JS SPA (frontend) + pywebview (desktop window)

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python main.py
```

Opens a desktop window via pywebview at `http://127.0.0.1:8000`. Falls back to browser if pywebview is not installed.

---

## Project Structure

```
UI_MANAGER/
├── main.py                  # Entry point: starts FastAPI + pywebview
├── config.yaml              # App config (ADB path, resolution, ports)
├── requirements.txt         # Python dependencies
│
├── backend/                 # FastAPI backend
│   ├── api.py               # All REST + WebSocket endpoints
│   ├── config.py            # Config loader (reads config.yaml)
│   ├── websocket.py         # WebSocketManager for real-time events
│   ├── core/                # Core logic modules
│   │   ├── adb_helper.py    # ADB device discovery & commands
│   │   ├── emulator.py      # EmulatorManager (ADB-based device registry)
│   │   ├── ldplayer_manager.py  # LDPlayer CLI wrapper (ldconsole.exe)
│   │   ├── macro_replay.py  # ★ ADB-based macro replay engine
│   │   ├── navigator.py     # Screen navigation helper
│   │   ├── ocr_engine.py    # Tesseract OCR wrapper
│   │   └── validator.py     # Data validation
│   ├── models/              # Pydantic models
│   ├── storage/             # SQLite database layer
│   └── tasks/               # Task queue (background jobs)
│
├── frontend/                # Vanilla JS Single Page Application
│   ├── index.html           # Main HTML (loads all CSS + JS)
│   ├── css/
│   │   ├── design-system.css    # CSS variables, tokens, colors
│   │   ├── layout.css           # Sidebar, header, grid, tab bar
│   │   ├── components.css       # Cards, badges, buttons, macro cards
│   │   └── animations.css       # Transitions, keyframes
│   └── js/
│       ├── app.js               # SPA router, WebSocket wiring
│       ├── api.js               # API client (fetch wrapper + WS manager)
│       ├── components/
│       │   ├── device-card.js   # Device card component
│       │   ├── notification.js  # NotificationManager (dropdown)
│       │   └── toast.js         # Toast notifications
│       └── pages/
│           ├── dashboard.js     # Dashboard page
│           ├── emulators.js     # ★ Emulator management (all instances)
│           ├── task-runner.js   # ★ Actions page (tabs + macros + scans)
│           ├── history.js       # History page
│           └── settings.js      # Settings page
│
├── data/                    # Runtime data
│   └── coordinate_maps/     # OCR coordinate configs per resolution
│
└── SAMPLE/                  # Reference design project
```

---

## Architecture

### Backend (FastAPI)

**Entry Point:** `main.py` → starts Uvicorn server → `backend/api.py` mounts all routes.

**Config:** `config.yaml` → loaded by `backend/config.py` (singleton `config` object). Key fields:
- `adb_path`: Path to LDPlayer's `adb.exe` (e.g., `C:\LDPlayer\LDPlayer9\adb.exe`)
- `resolution`: Target emulator resolution (e.g., `960x540`)
- `server_port`: API port (default 8000)

**WebSocket:** `backend/websocket.py` — `WebSocketManager` with:
- `broadcast(event: str, data: dict)` — async, sends to all clients
- `broadcast_sync(event: str, data: dict)` — sync wrapper for use from threads

### Frontend (Vanilla JS SPA)

**Router:** `app.js` manages page navigation. Each page is a JS object with:
- `render()` → returns HTML string
- `init()` → called after DOM insertion (async, fetch data)
- `destroy()` → cleanup (clear intervals, etc.)

**API Client:** `api.js` provides `API` object with methods like:
- `API.getDevices()`, `API.getAllEmulators()`, `API.getMacros()`
- `API.runMacro(index, filename)`, `API.launchEmulator(index)`

**WebSocket Client:** `WSManager` in `api.js` auto-reconnects and dispatches events to page handlers via `page.updateFromWS(event, data)`.

---

## Key Features

### 1. Emulator Management (`emulators.js` + `ldplayer_manager.py`)

Lists **ALL** LDPlayer instances (online + offline) via `ldconsole.exe list2`.

| API Endpoint              | Method | Description                    |
|---------------------------|--------|--------------------------------|
| `/api/emulators/all`      | GET    | List all instances (index, name, running, resolution, DPI) |
| `/api/emulators/launch`   | POST   | Start instance by `?index=N`   |
| `/api/emulators/quit`     | POST   | Stop instance by `?index=N`    |

**Frontend:** `emulators.js` displays instances as cards with Start/Stop buttons and 5s auto-refresh polling.

**LDPlayer Index → ADB Serial mapping:**
```
ADB serial = "emulator-{5554 + index * 2}"
Example: index 1 → emulator-5556
```

---

### 2. Macro Replay Engine (`macro_replay.py`)

Parses LDPlayer `.record` files and replays touch operations via ADB.

#### How It Works

1. `.record` files are JSON with `operations[]` array containing `PutMultiTouch` events
2. Each event has `timing` (ms), `points[]` with `{x, y, id, state}`
3. `state=1` = touch DOWN, `state=0` = touch UP, empty points = release
4. Engine detects tap vs swipe by comparing DOWN/UP distance (threshold: 10px)
5. Runs in **background thread** — non-blocking API

#### Coordinate System

```
.record coordinates = screen_pixels × COORD_SCALE (20)
Example: record x=17940 → ADB pixel = 17940/20 = 897 (on 960px wide screen)
```

**Cross-resolution scaling:** If record was made on 960×540 but target is different:
```python
actual_x = (record_x / 20) * (target_width / record_width)
```

#### API Endpoints

| Endpoint              | Method | Description                          |
|-----------------------|--------|--------------------------------------|
| `/api/macros/list`    | GET    | List all `.record` files             |
| `/api/macros/info`    | GET    | Record metadata (`?index=N&filename=X`) |
| `/api/macros/run`     | POST   | Start replay (`?index=N&filename=X`) → background thread |
| `/api/macros/stop`    | POST   | Stop running replay                  |
| `/api/macros/status`  | GET    | Status of all running macros         |

#### `.record` File Format

```json
{
  "operations": [
    {
      "timing": 1588,
      "operationId": "PutMultiTouch",
      "points": [{"id": 1, "x": 11040, "y": 4380, "state": 1}]
    }
  ],
  "recordInfo": {
    "loopType": 0,
    "loopTimes": 1,
    "circleDuration": 6150,
    "resolutionWidth": 960,
    "resolutionHeight": 540
  }
}
```

#### `.record` File Location

```
C:\LDPlayer\LDPlayer9\vms\operationRecords\*.record
```

---

### 3. Actions Page (`task-runner.js`)

Three-tab layout with shared Activity Feed:

```
┌────────────────────────────────────────────────┐
│ [📱 Target Emulators] [🔴 Recorder] [🔍 Scan] │  ← Tab Bar
├────────────────────────────────────────────────┤
│ Tab Content (switches per tab)                 │
├────────────────────────────────────────────────┤
│ Activity Feed (shared, shows all events)       │
└────────────────────────────────────────────────┘
```

**Tab 1 — Target Emulators:** Checkbox list of RUNNING emulators. Selection persists across tabs via `_selectedEmus` Set.

**Tab 2 — Operation Recorder:** Grid of macro `.record` cards with "Run Script" button. When running:
- Button changes to "Running..." (disabled)
- Status bar shows spinner + elapsed timer
- On completion: green checkmark + duration

**Tab 3 — Scan Operations:** 4 scan cards (Profile, Resources, Hall, Full Scan).

**State Flow:**
1. User selects emulators in Tab 1
2. Switches to Tab 2 or 3 → target badge shows "✓ N emulator(s) targeted"
3. Clicks "Run Script" → `API.runMacro(index, filename)` → backend starts thread
4. Activity Feed logs events with timestamps

---

## CSS Architecture

```
design-system.css   → CSS variables (--primary, --border, --radius-lg, etc.)
layout.css          → Page structure (sidebar, header, grids, tab bar)
components.css      → UI components (cards, badges, buttons, macro status bars)
animations.css      → @keyframes and transitions
```

Key CSS classes for the Actions page:
- `.actions-tabbar` / `.actions-tab` / `.actions-tab.active` — Tab bar
- `.tab-panel` / `.tab-panel-header` / `.tab-panel-body` — Tab content panels
- `.emu-check-item` / `.emu-check-item.selected` — Emulator checkboxes
- `.macro-card` / `.macro-card-status` — Macro script cards
- `.macro-running-bar` / `.macro-elapsed` — Running state indicator
- `.macro-done-bar` — Completion indicator
- `.tab-count` — Badge counter on tab button
- `.emu-selected-badge` — Target selection badge in Recorder/Scan tabs
- `.feed-item` / `.feed-dot.active` / `.feed-dot.done` / `.feed-dot.fail` — Activity Feed

---

## WebSocket Events

| Event              | Direction    | Data                                    |
|--------------------|--------------|-----------------------------------------|
| `device_update`    | Server → UI  | `{serial, status}`                      |
| `task_started`     | Server → UI  | `{serial, task_type}`                   |
| `task_progress`    | Server → UI  | `{serial, step, progress}`              |
| `task_completed`   | Server → UI  | `{serial, task_type, result}`           |
| `task_failed`      | Server → UI  | `{serial, error}`                       |
| `macro_started`    | Server → UI  | `{serial, filename, total_ops, duration_ms}` |
| `macro_progress`   | Server → UI  | `{serial, filename, completed, total}`  |
| `macro_completed`  | Server → UI  | `{serial, filename, elapsed_ms}`        |
| `macro_failed`     | Server → UI  | `{serial, filename, error}`             |

Frontend handles these in `TaskRunnerPage.updateFromWS(event, data)` and `app.js` WS dispatcher.

---

## Known Issues / TODO

- [ ] **Tab UI consistency**: Some spacing/styling differences between the 3 tabs need polishing
- [ ] **Macro progress tracking**: Frontend doesn't yet consume `macro_progress` WS events in real-time
- [ ] **Macro stop button**: No "Stop" button on macro cards — API exists (`POST /api/macros/stop`) but no frontend UI
- [ ] **Activity Feed persistence**: Feed clears on page navigation (no persistence)
- [ ] **Responsive**: Tab bar scrolls horizontally on narrow screens but tab content may overflow
- [ ] **Error handling**: Some API error cases show generic "Network Error" instead of specific messages

---

## Dependencies

```
fastapi
uvicorn
pyyaml
pillow
pytesseract
aiofiles
pywebview        # Optional, for native desktop window
```

## External Tools

- **LDPlayer 9** — `ldconsole.exe` and `adb.exe` at path specified in `config.yaml`
- **Tesseract OCR** — for OCR scan features (path in `config.yaml`)

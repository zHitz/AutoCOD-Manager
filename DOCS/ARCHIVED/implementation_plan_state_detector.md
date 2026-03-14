# Optimize [state_detector.py](file:///f:/COD_CHECK/UI_MANAGER/backend/core/workflow/state_detector.py) — Performance & Detection Accuracy

## Current Performance Profile

Mỗi lần [check_state_full()](file:///f:/COD_CHECK/UI_MANAGER/backend/core/workflow/state_detector.py#289-308) được gọi, nó thực hiện:

```
1. ADB screencap (300-500ms)         ← 70% thời gian
2. matchTemplate × N templates        ← 25% thời gian
3. minMaxLoc per match                 ← 5% thời gian
```

Hiện tại có **~40 templates** loaded. [check_state_full()](file:///f:/COD_CHECK/UI_MANAGER/backend/core/workflow/state_detector.py#289-308) phải chạy `matchTemplate` trên **full 960×540 screen** cho từng template → rất tốn CPU, đặc biệt khi số template tăng.

---

## Proposed Optimizations

### OPT-1: ROI Cropping — Chỉ scan vùng cần thiết

> **Impact: Giảm 60-80% thời gian matchTemplate**

Hiện tại mỗi template scan **TOÀN BỘ** screen (960×540 = 518,400 pixels). Nhưng thực tế:
- Lobby icons (hammer, magnifier) chỉ nằm ở **góc dưới trái**
- Loading screen indicator nằm ở **giữa màn hình**
- Construction icons nằm ở **vùng trên cùng**
- Profile/Menu buttons nằm ở **góc trên trái**

**Giải pháp:** Thêm `roi` (Region of Interest) vào config — mỗi template chỉ scan vùng nhỏ thay vì full screen.

```python
# BEFORE: scan full screen
self.state_configs = {
    "lobby_hammer.png": "IN-GAME LOBBY (IN_CITY)",
}

# AFTER: scan only bottom-left 200×150 region
self.state_configs = {
    "lobby_hammer.png": {
        "state": "IN-GAME LOBBY (IN_CITY)",
        "roi": (0, 390, 200, 540),   # (x1, y1, x2, y2)
    },
}
```

Matching code:
```python
if roi:
    x1, y1, x2, y2 = roi
    cropped = screen[y1:y2, x1:x2]
    res = cv2.matchTemplate(cropped, template, cv2.TM_CCOEFF_NORMED)
else:
    res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
```

> [!IMPORTANT]
> Cần đo toạ độ ROI chính xác cho từng template. Có thể tạo tool hỗ trợ: chụp screenshot, vẽ rectangle, output ROI coords.

---

### OPT-2: Grayscale Matching — Giảm 66% data xử lý

> **Impact: Giảm ~50% thời gian matchTemplate**

`matchTemplate` trên ảnh COLOR (3 channels BGR) xử lý **gấp 3 lần** so với GRAYSCALE (1 channel):

```python
# BEFORE: Color matching (960×540×3 = 1,555,200 values)
img = cv2.imread(path, cv2.IMREAD_COLOR)
res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)

# AFTER: Grayscale matching (960×540×1 = 518,400 values)
img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
screen_gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)  # convert 1 lần
res = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)
```

**Rủi ro:** Một số template có thể giảm accuracy nếu chỉ khác nhau bởi màu sắc (không phải hình dạng). Cần test threshold lại.

**Giải pháp an toàn:** Load CẢ HAI version (color + gray), dùng gray cho matching nhanh, fallback color khi cần verify.

---

### OPT-3: Early Exit — Cache Last State

> **Impact: ~90% lần gọi trả kết quả ngay lập tức (0 template matching)**

Nguyên lý: Game state thường **không đổi giữa 2 lần check liên tiếp**. Nếu lần trước đã match "`IN-GAME LOBBY (IN_CITY)`", lần này check nó trước:

```python
self._last_matched_state = None
self._last_matched_template_idx = None

def _match_state_from_screen(self, screen, threshold=0.8):
    # Try last matched state FIRST (90% hit rate)
    if self._last_matched_state and self._last_matched_state in self.templates:
        for template in self.templates[self._last_matched_state]:
            res = cv2.matchTemplate(screen, template, ...)
            if max_val >= threshold:
                return self._last_matched_state  # FAST PATH: 1 match instead of N

    # Full scan only if cache miss
    for state_name in priority_checks:
        ...

    self._last_matched_state = result  # Update cache
    return result
```

---

### OPT-4: DRY — Deduplicate [_load_templates](file:///f:/COD_CHECK/UI_MANAGER/backend/core/workflow/state_detector.py#114-201)

> **Impact: Code quality, không ảnh hưởng performance**

Hiện tại [_load_templates](file:///f:/COD_CHECK/UI_MANAGER/backend/core/workflow/state_detector.py#114-201) có **7 copy-paste blocks** gần giống nhau. Gom thành 1 method:

```python
def _load_template_group(self, configs: dict, target_dict: dict, label: str):
    """Generic template loader for any category."""
    for filename, name in configs.items():
        path = os.path.join(self.templates_dir, filename)
        if not os.path.exists(path):
            print(f"[WARNING] {label} template missing: {path}")
            continue
        img = cv2.imread(path, cv2.IMREAD_COLOR)
        if img is not None:
            target_dict.setdefault(name, []).append(img)

def _load_templates(self):
    print("[INFO] Pre-loading image templates into RAM...")
    self._load_template_group(self.state_configs, self.templates, "State")
    self._load_template_group(self.construction_configs, self.construction_templates, "Construction")
    self._load_template_group(self.special_configs, self.special_templates, "Special")
    self._load_template_group(self.activity_configs, self.activity_templates, "Activity")
    self._load_template_group(self.alliance_configs, self.alliance_templates, "Alliance")
    self._load_template_group(self.icon_configs, self.icon_templates, "Icon")
    self._load_template_group(self.account_configs, self.account_templates, "Account")
```

---

### OPT-5: Screencap Pipeline — Giảm latency ADB

> **Impact: Giảm 100-200ms per screencap**

Hiện tại dùng `subprocess.run()` (blocking). Có thể tối ưu:

**5a. Resize screenshot ngay sau capture:**
```python
img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
# Resize to half → 4x fewer pixels cho matchTemplate
img_small = cv2.resize(img, (480, 270))
```
> [!WARNING]
> Resize đòi hỏi templates CŨNG phải resize tương ứng khi load. Phức tạp hơn nhưng hiệu quả cao.

**5b. Cache screenshot trong thời gian ngắn:**
```python
self._screen_cache = None
self._screen_cache_time = 0

def screencap_memory(self, serial, max_age_ms=200):
    now = time.time() * 1000
    if self._screen_cache is not None and (now - self._screen_cache_time) < max_age_ms:
        return self._screen_cache  # Return cached, skip ADB
    # ... actual ADB call ...
    self._screen_cache = img
    self._screen_cache_time = now
    return img
```

---

## Implementation Priority

| # | Optimization | Effort | Impact | Risk | Recommend |
|---|-------------|--------|--------|------|-----------|
| OPT-4 | DRY [_load_templates](file:///f:/COD_CHECK/UI_MANAGER/backend/core/workflow/state_detector.py#114-201) | Low | Clean code | None | ✅ Do first |
| OPT-3 | Early exit cache | Low | High (skip 90% matching) | None | ✅ Do second |
| OPT-2 | Grayscale matching | Medium | High (3x faster match) | Need re-test thresholds | ✅ Do third |
| OPT-1 | ROI cropping | Medium-High | Very high (5-10x faster) | Need ROI coords per template | ✅ Do fourth |
| OPT-5b | Screenshot cache | Low | Medium (skip ADB calls) | Stale data risk | ⚠️ Optional |
| OPT-5a | Resize pipeline | High | Very high | Requires template rebuild | ❌ Later |

## Verification Plan

### Benchmark Script
Tạo script so sánh performance before/after:
- Chạy [check_state_full()](file:///f:/COD_CHECK/UI_MANAGER/backend/core/workflow/state_detector.py#289-308) 50 lần liên tiếp
- Đo average time per call
- So sánh accuracy (cùng screenshot, cùng kết quả)

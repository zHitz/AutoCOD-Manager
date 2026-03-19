"""
Policy Automation V3 — Smart Path Engine
==========================================
Optimized: only enacts policies needed for the target path.

Strategy:
  1. Load progress (last completed column)
  2. Jump to next column (col N+1)
  3. Tap target policy → check popup:
     - ENACT → enact → save progress → done
     - GO    → tap GO → game navigates to prerequisite → enact that
     - SELECT → handle governance → retry
     - LOCKED → all prereqs locked, try from col 0
  4. After GO-chain enact, next run tries same col again

Usage:
    from backend.core.workflow.policy.engine import PolicyV3Engine

    engine = PolicyV3Engine(serial, detector, adb_path, account_id="12345")
    result = engine.run()
"""
import time
import cv2
import numpy as np
import subprocess

from backend.core.workflow import adb_helper
from backend.core.workflow.policy.data import (
    COLUMNS, COLUMN_Y_POSITIONS, SCROLL_RIGHT, SCROLL_LEFT_RESET,
    CLOSE_POPUP_POS, GOVERNANCE_CARD_POSITIONS,
    MAX_TARGET_COL, COL_SIZES,
    load_progress, save_progress,
)


def _log(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [V3] {msg}")


# ═══════════════════════════════════════════════════════════
# POPUP DETECTION & BUTTON TAPPING
# ═══════════════════════════════════════════════════════════

def detect_policy_popup(serial, detector):
    """Detect which popup is showing after tapping a policy icon.

    Returns one of:
        "ENACT"            — ENACT button visible (can enact policy)
        "REQUIREMENTS_GO"  — GO button visible (prerequisites needed)
        "SELECT"           — Governance SELECT popup (need to choose card)
        "LOCKED"           — No actionable button found
    """
    # Check ENACT button first (highest priority)
    enact = detector.check_activity(
        serial, target="POLICY_ENACT_BTN", threshold=0.85)
    if enact:
        return "ENACT"

    # Check GO button (requirements popup)
    go = detector.check_activity(
        serial, target="POLICY_GO_BTN", threshold=0.92)
    if go:
        return "REQUIREMENTS_GO"

    # Check governance header (SELECT popup)
    gov = detector.check_special_state(
        serial, target="GOVERNANCE_HEADER", threshold=0.85)
    if gov:
        return "SELECT"

    return "LOCKED"


def _tap_policy_enact(serial, detector):
    """Find and tap the ENACT button.

    Returns True if tapped, False if not found.
    """
    match = detector.check_activity(
        serial, target="POLICY_ENACT_BTN", threshold=0.85)
    if match:
        _, x, y = match
        _log(f"  Tapping ENACT at ({x}, {y})...")
        adb_helper.tap(serial, x, y)
        return True
    _log("  ENACT button not found!")
    return False


def _tap_policy_go(serial, detector):
    """Find and tap the GO button in requirements popup.

    Returns True if tapped, False if not found.
    """
    match = detector.check_activity(
        serial, target="POLICY_GO_BTN", threshold=0.92)
    if match:
        _, x, y = match
        _log(f"  Tapping GO at ({x}, {y})...")
        adb_helper.tap(serial, x, y)
        return True
    _log("  GO button not found!")
    return False


# ═══════════════════════════════════════════════════════════
# COLUMN DETECTION (unchanged from previous version)
# ═══════════════════════════════════════════════════════════

def detect_column_x_positions(img, debug_path=None):
    """Detect column X centers from policy screen screenshot."""
    h, w = img.shape[:2]
    crop = img[55:500, :].copy()
    ch, cw = crop.shape[:2]

    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    blue_mask = cv2.inRange(hsv, (95, 60, 60), (125, 255, 255))

    # Green mask — catches policy icons (green squares) on fresh accounts
    green_mask = cv2.inRange(hsv, (35, 50, 50), (85, 255, 255))

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    _, bright_mask = cv2.threshold(gray, 60, 255, cv2.THRESH_BINARY)

    combined = cv2.bitwise_or(blue_mask, bright_mask)
    combined = cv2.bitwise_or(combined, green_mask)
    projection = np.sum(combined, axis=0).astype(float)

    kernel_size = 31
    smoothed = np.convolve(projection, np.ones(kernel_size) / kernel_size, mode='same')

    threshold = np.max(smoothed) * 0.15  # Lower threshold to catch 2-policy cols
    peaks = []
    in_peak = False
    peak_start = 0

    for x in range(len(smoothed)):
        if smoothed[x] > threshold:
            if not in_peak:
                in_peak = True
                peak_start = x
        else:
            if in_peak:
                in_peak = False
                if x - peak_start > 30:
                    peaks.append((peak_start + x) // 2)
    if in_peak and len(smoothed) - peak_start > 30:
        peaks.append((peak_start + len(smoothed)) // 2)

    merged = []
    for p in peaks:
        if merged and abs(p - merged[-1]) < 100:
            merged[-1] = (merged[-1] + p) // 2
        else:
            merged.append(p)

    if debug_path:
        debug = crop.copy()
        proj_norm = (smoothed / max(smoothed.max(), 1) * 100).astype(int)
        for x_px in range(len(proj_norm)):
            y_bar = ch - proj_norm[x_px]
            cv2.line(debug, (x_px, ch), (x_px, max(y_bar, 0)), (0, 100, 0), 1)
        for i, cx in enumerate(merged):
            cv2.line(debug, (cx, 0), (cx, ch), (0, 255, 0), 2)
            cv2.putText(debug, f"C{i}:{cx}", (cx + 3, 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        cv2.imwrite(debug_path, debug)

    return merged


def detect_column_size(img, x_center):
    """Detect column size (2/3/4) by brightness at known Y slots."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    x_lo = max(0, x_center - 20)
    x_hi = min(img.shape[1], x_center + 20)
    strip = gray[:, x_lo:x_hi]

    y_checks = {4: [80, 210, 330, 460], 3: [130, 260, 440], 2: [130, 400]}
    best_size, best_score = 3, 0.0

    for size, ys in y_checks.items():
        score = sum(1 for y in ys
                    if y < strip.shape[0] and
                    np.mean(strip[max(0, y - 15):min(strip.shape[0], y + 15), :]) > 40)
        frac = score / len(ys)
        if frac > best_score:
            best_score = frac
            best_size = size

    return best_size


def identify_columns(img, detected_x_list, min_start=0):
    """Map detected X positions to column indices via size fingerprint."""
    if not detected_x_list:
        return []

    detected_sizes = [detect_column_size(img, x) for x in detected_x_list]
    n = len(detected_sizes)
    best_start, best_score = min_start, -1

    for start in range(min_start, len(COL_SIZES) - n + 1):
        score = sum(1 for i in range(n) if detected_sizes[i] == COL_SIZES[start + i])
        if score > best_score:
            best_score = score
            best_start = start

    _log(f"Sizes {detected_sizes} → cols {best_start}-{best_start + n - 1} ({best_score}/{n})")

    return [(best_start + i, x) for i, x in enumerate(detected_x_list)
            if best_start + i < len(COLUMNS)]


# ═══════════════════════════════════════════════════════════
# V3 SMART PATH ENGINE
# ═══════════════════════════════════════════════════════════

class PolicyV3Engine:
    """
    Smart-path policy automation engine.

    Strategy: jump to next incomplete column → tap target policy →
    follow GO chain for prerequisites → enact → save progress.
    """

    def __init__(self, serial, detector, adb_path, account_id="default", debug_dir=None):
        self.serial = serial
        self.detector = detector
        self.adb_path = adb_path
        self.account_id = account_id
        self.debug_dir = debug_dir

    def _screencap(self):
        cmd = [self.adb_path, "-s", self.serial, "exec-out", "screencap", "-p"]
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        try:
            r = subprocess.run(cmd, capture_output=True, startupinfo=si, timeout=5)
            if r.stdout:
                return cv2.imdecode(np.frombuffer(r.stdout, np.uint8), cv2.IMREAD_COLOR)
        except Exception as e:
            _log(f"Screencap error: {e}")
        return None

    def _close_popup(self):
        adb_helper.tap(self.serial, CLOSE_POPUP_POS[0], CLOSE_POPUP_POS[1])
        time.sleep(1)

    def _ensure_at_home(self):
        """Ensure we're on policy screen at home position (screen 0).
        Entering Season Policies always starts at screen 0, no scroll needed.
        If already on policy screen, exit and re-enter to reset position."""
        is_policy = self.detector.check_special_state(
            self.serial, target="POLICY_SCREEN", threshold=0.80)

        if is_policy:
            _log("Already on policy screen → back + re-enter to reset")
            adb_helper.press_back(self.serial)
            time.sleep(2)
            # Now on Season menu, tap Policies to re-enter
            adb_helper.tap(self.serial, 890, 260)
            time.sleep(3)
        else:
            # Navigate from lobby
            state = self.detector.check_state(self.serial)
            LOBBY = ["IN-GAME LOBBY (IN_CITY)", "IN-GAME LOBBY (OUT_CITY)"]
            if state in LOBBY:
                _log("Navigating: Lobby → Season → Policies")
                adb_helper.tap(self.serial, 815, 80)
                time.sleep(3)
                adb_helper.tap(self.serial, 890, 260)
                time.sleep(3)
            else:
                _log(f"Unknown state: {state}, trying Season Policies tap")
                adb_helper.tap(self.serial, 890, 260)
                time.sleep(3)

    def _scroll_right(self):
        s = SCROLL_RIGHT
        adb_helper.swipe(self.serial, s["start_x"], s["y"], s["end_x"], s["y"],
                         duration=s["duration"])
        time.sleep(1.5)

    def _get_target_y(self, col_idx):
        """Get Y position for the critical-path policy in this column (fallback)."""
        col = COLUMNS[col_idx]
        pos_key = col.get("target_pos")
        y_map = COLUMN_Y_POSITIONS.get(col["size"], {})
        return y_map.get(pos_key, 260)

    def _detect_icon_y_positions(self, col_x, half_width=45):
        """Detect policy icon Y centers within column strip using green projection.
        
        Returns sorted list of Y centers (absolute screen coordinates).
        """
        img = self._screencap()
        if img is None:
            return []

        h, w = img.shape[:2]
        min_y, max_y = 55, 500
        x_lo = max(0, col_x - half_width)
        x_hi = min(w, col_x + half_width)
        crop = img[min_y:max_y, x_lo:x_hi]

        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        green_mask = cv2.inRange(hsv, (35, 50, 50), (85, 255, 255))

        # Horizontal projection
        proj = np.sum(green_mask, axis=1).astype(float)
        kernel = np.ones(15) / 15
        smoothed = np.convolve(proj, kernel, mode='same')

        threshold = max(smoothed.max() * 0.25, 500)
        peaks = []
        in_peak = False
        peak_start = 0

        for y in range(len(smoothed)):
            if smoothed[y] > threshold:
                if not in_peak:
                    in_peak = True
                    peak_start = y
            else:
                if in_peak:
                    in_peak = False
                    if y - peak_start > 10:
                        center_y = (peak_start + y) // 2 + min_y
                        peaks.append(center_y)
        if in_peak and len(smoothed) - peak_start > 10:
            center_y = (peak_start + len(smoothed)) // 2 + min_y
            peaks.append(center_y)

        return peaks

    def _get_tap_targets(self, col_idx, col_x):
        """Get ordered list of (label, y) tap targets for this column.
        
        Uses dynamic icon detection + column config to determine tap order.
        For governance cols with branches: prioritize bottom branch.
        For cols with tap_order: follow specified order.
        Fallback to hardcoded positions if detection fails.
        """
        col = COLUMNS[col_idx]
        icon_ys = self._detect_icon_y_positions(col_x)
        expected_size = col["size"]

        if icon_ys:
            _log(f"  Dynamic icons at X={col_x}: Y={icon_ys}")

        # Check for tap_order config (e.g., Col 4: ["mid", "bottom"])
        tap_order = col.get("tap_order")
        if tap_order:
            if icon_ys and len(icon_ys) >= expected_size:
                # Dynamic detection succeeded — map to detected positions
                pos_map = {"top": 0, "mid": len(icon_ys) // 2, "bottom": len(icon_ys) - 1}
                result = []
                for pos_key in tap_order:
                    idx = pos_map.get(pos_key, 0)
                    if idx < len(icon_ys):
                        result.append((pos_key, icon_ys[idx]))
                if result:
                    return result
            else:
                # Dynamic detection failed — use hardcoded Y positions
                y_map = COLUMN_Y_POSITIONS.get(expected_size, {})
                result = []
                for pos_key in tap_order:
                    y_val = y_map.get(pos_key)
                    if y_val is not None:
                        result.append((pos_key, y_val))
                if result:
                    _log(f"  Using hardcoded tap_order: {result}")
                    return result

        # For governance columns: if governance already done, try bottom branch first
        gov = col.get("governance", {})
        branches = gov.get("branches")
        if branches and icon_ys and len(icon_ys) >= expected_size:
            result = []
            mid = len(icon_ys) // 2
            for i in range(mid, len(icon_ys)):
                result.append((f"icon_{i}", icon_ys[i]))
            for i in range(mid):
                result.append((f"icon_{i}", icon_ys[i]))
            return result

        # Default: single target position
        y = self._get_target_y(col_idx)

        if icon_ys:
            closest = min(icon_ys, key=lambda iy: abs(iy - y))
            return [("target", closest)]

        return [("target", y)]

    def _handle_governance(self, col_idx):
        """Select governance card: tap card to highlight → tap SELECT to confirm."""
        col = COLUMNS[col_idx]
        gov = col.get("governance", {})

        if gov.get("skip"):
            _log(f"Governance col {col_idx}: SKIP (not on target path)")
            self._close_popup()
            return False

        # Debug: capture governance popup
        if self.debug_dir:
            import os
            dbg = self._screencap()
            if dbg is not None:
                cv2.imwrite(
                    os.path.join(self.debug_dir, f"v3_gov_before.png"), dbg)

        # Step 1: Tap the desired card to highlight it
        card_idx = gov.get("card", 0)
        card_pos = GOVERNANCE_CARD_POSITIONS[card_idx]
        _log(f"Governance col {col_idx}: tapping card {card_idx} at {card_pos}")
        adb_helper.tap(self.serial, card_pos[0], card_pos[1])
        time.sleep(1.5)

        # Step 2: Tap SELECT button to confirm
        SELECT_BTN = (480, 415)
        _log(f"  Tapping SELECT button at {SELECT_BTN}")
        adb_helper.tap(self.serial, SELECT_BTN[0], SELECT_BTN[1])
        time.sleep(3)

        # Debug: capture after SELECT (popup should have closed)
        if self.debug_dir:
            dbg = self._screencap()
            if dbg is not None:
                cv2.imwrite(
                    os.path.join(self.debug_dir, f"v3_gov_after.png"), dbg)

        return True

    def _post_enact_check(self):
        """Handle post-ENACT edge cases.
        
        1. REPLENISH RESOURCES popup (not enough points) → back, return False
        2. Alliance Help button (bottom-right) → tap if found
        
        Returns: True if ENACT succeeded, False if REPLENISH blocked it.
        """
        time.sleep(2)

        # Check for REPLENISH RESOURCES popup
        replenish = self.detector.check_activity(
            self.serial, target="POLICY_REPLENISH", threshold=0.85
        )
        if replenish:
            _log("  ⚠ REPLENISH RESOURCES popup — not enough points!")
            self._close_popup()
            time.sleep(1)
            return False

        # Check for Alliance Help button (bottom-right corner ~910, 510)
        alliance_help = self.detector.check_activity(
            self.serial, target="POLICY_ALLIANCE_HELP", threshold=0.85
        )
        if alliance_help:
            _, ax, ay = alliance_help
            _log(f"  Tapping Alliance Help at ({ax}, {ay})")
            adb_helper.tap(self.serial, ax, ay)
            time.sleep(1)
        else:
            _log("  No Alliance Help button (may not be in alliance)")

        return True

    def _scroll_to_column(self, target_col):
        """
        Scroll until target column is visible on screen.
        Re-enters policy screen to guarantee starting at screen 0.
        Returns: (col_idx, x_center) for the target column, or None.
        """
        self._ensure_at_home()

        # Track min_start for identity matching
        last_max_col = -1

        for scroll_num in range(5):
            if scroll_num > 0:
                self._scroll_right()

            img = self._screencap()
            if img is None:
                continue

            debug_path = None
            if self.debug_dir:
                import os
                debug_path = os.path.join(self.debug_dir, f"v3_nav_s{scroll_num}.png")

            detected_x = detect_column_x_positions(img, debug_path)
            if not detected_x:
                continue

            min_start = max(last_max_col - 2, 0) if last_max_col >= 0 else 0
            identified = identify_columns(img, detected_x, min_start)

            if identified:
                last_max_col = max(ci for ci, _ in identified)

            # Check if target is visible
            for col_idx, x_center in identified:
                if col_idx == target_col:
                    _log(f"Column {target_col} found at X={x_center}")
                    return col_idx, x_center

            # Check if we've scrolled past target
            if identified and identified[-1][0] > target_col:
                _log(f"Scrolled past col {target_col}")
                break

        _log(f"Column {target_col} NOT found after scrolling!")
        return None

    def _follow_go_chain(self, max_depth=10):
        """
        Follow GO button chain: tap GO → game navigates to prerequisite → check popup.
        Repeats until finding ENACT or hitting max depth.

        Returns:
            "ENACT_SUCCESS" — found and enacted a prerequisite
            "LOCKED"        — chain ended without ENACT
            "SELECT"        — hit governance popup
        """
        for depth in range(max_depth):
            _log(f"GO chain depth {depth}: tapping GO...")
            success = _tap_policy_go(self.serial, self.detector)
            if not success:
                _log("  GO button not found")
                return "LOCKED"

            time.sleep(4)  # Wait for game scroll animation + popup load

            # Debug screenshot
            if self.debug_dir:
                import os
                dbg = self._screencap()
                if dbg is not None:
                    cv2.imwrite(
                        os.path.join(self.debug_dir, f"v3_go_d{depth}.png"), dbg)

            # After GO, popup appears at different position than normal.
            # Use FULL FRAME to search for ENACT button (not cropped POPUP_ROI)
            full_frame = self.detector.get_frame(self.serial)
            if full_frame is None:
                return "LOCKED"

            # Check ENACT on full frame
            enact = self.detector.check_activity(
                self.serial, target="POLICY_ENACT_BTN", threshold=0.85,
                frame=full_frame)
            if enact:
                _, ex, ey = enact
                _log(f"  >>> Found ENACT at ({ex}, {ey}) via GO chain!")
                adb_helper.tap(self.serial, ex, ey)
                if not self._post_enact_check():
                    return "ALL_LOCKED"  # REPLENISH — not enough points
                self._close_popup()
                return "ENACT_SUCCESS"

            # Check GO on full frame
            go = self.detector.check_activity(
                self.serial, target="POLICY_GO_BTN", threshold=0.92,
                frame=full_frame)
            if go:
                _log(f"  Another GO found — continuing chain")
                popup = "REQUIREMENTS_GO"
            else:
                # Check governance
                gov = self.detector.check_special_state(
                    self.serial, target="GOVERNANCE_HEADER", threshold=0.85,
                    frame=full_frame)
                if gov:
                    popup = "SELECT"
                else:
                    popup = "LOCKED"

            _log(f"  After GO (full-frame): popup = {popup}")

            if popup == "ENACT":
                _log("  >>> Found ENACT via GO chain!")
                success = _tap_policy_enact(self.serial, self.detector)
                if success and not self._post_enact_check():
                    return "ALL_LOCKED"  # REPLENISH — not enough points
                self._close_popup()
                return "ENACT_SUCCESS" if success else "LOCKED"

            elif popup == "SELECT":
                _log("  Hit governance in GO chain")
                return "SELECT"

            elif popup == "REQUIREMENTS_GO":
                # Another GO — continue chain
                continue

            elif popup == "LOCKED":
                # Could be: (a) prereq mid-research, or (b) popup not loaded yet
                # Retry once with extra wait
                _log("  LOCKED — retrying with extra wait...")
                time.sleep(2)
                popup2 = detect_policy_popup(self.serial, self.detector)
                _log(f"  Retry: popup = {popup2}")
                if popup2 == "ENACT":
                    _log("  >>> Found ENACT on retry!")
                    success = _tap_policy_enact(self.serial, self.detector)
                    if success and not self._post_enact_check():
                        return "ALL_LOCKED"  # REPLENISH
                    self._close_popup()
                    return "ENACT_SUCCESS" if success else "LOCKED"
                elif popup2 == "REQUIREMENTS_GO":
                    continue
                else:
                    self._close_popup()
                    return "LOCKED"

        _log("  GO chain hit max depth!")
        self._close_popup()
        return "LOCKED"

    def run(self):
        """
        Run one smart-path cycle.

        Flow:
          1. Load progress → get next column
          2. Scroll to that column
          3. Tap target policy → handle popup
          4. If GO → follow chain to prerequisite → enact
          5. If ENACT → enact → update progress
          6. If SELECT → handle governance → update progress

        Returns:
          "ENACT_SUCCESS"      — policy enacted, progress NOT updated (prerequisite)
          "TARGET_ENACTED"     — target column policy enacted, progress updated
          "GOVERNANCE_DONE"    — governance selected, progress updated
          "ALL_LOCKED"         — no actionable policy found
          "TARGET_REACHED"     — past final target column
        """
        progress = load_progress(self.account_id)
        start_col = progress["last_col"] + 1

        _log("=" * 50)
        _log(f"SMART PATH RUN — start_col={start_col}, target={MAX_TARGET_COL}")
        _log(f"Progress: {progress}")
        _log("=" * 50)

        if start_col > MAX_TARGET_COL:
            _log("Already past target! Nothing to do.")
            return "TARGET_REACHED"

        col = COLUMNS[start_col]

        # Skip columns with no policies
        if col["size"] == 0:
            save_progress(start_col, self.account_id)
            return self.run()  # Recurse to next column

        # ── Navigate to target column ──
        result = self._scroll_to_column(start_col)
        if result is None:
            _log(f"Could not find col {start_col} on screen!")
            return "ALL_LOCKED"

        col_idx, x_center = result

        # ── Check if governance column ──
        if "governance" in col:
            _log(f"Col {col_idx}: governance column")
            # Tap any policy to trigger governance popup
            y = self._get_target_y(col_idx)
            adb_helper.tap(self.serial, x_center, y)
            time.sleep(2)

            popup = detect_policy_popup(self.serial, self.detector)
            _log(f"  Popup: {popup}")

            if popup == "SELECT":
                handled = self._handle_governance(col_idx)
                if handled:
                    save_progress(col_idx, self.account_id)
                    _log(f"Col {col_idx}: governance done → saved progress")
                    return "GOVERNANCE_DONE"
                else:
                    return "ALL_LOCKED"

            elif popup == "ENACT":
                _log("  >>> ENACTING (governance already selected)!")
                success = _tap_policy_enact(self.serial, self.detector)
                if not success or not self._post_enact_check():
                    self._close_popup()
                    return "ALL_LOCKED"  # REPLENISH or ENACT failed
                self._close_popup()
                save_progress(col_idx, self.account_id)
                return "TARGET_ENACTED"

            elif popup == "REQUIREMENTS_GO":
                # Governance needs prerequisite from previous column
                _log("  Governance has GO → following prerequisite chain...")
                go_result = self._follow_go_chain()
                if go_result == "ENACT_SUCCESS":
                    _log("  Prerequisite enacted! (retry same col next run)")
                    return "ENACT_SUCCESS"
                else:
                    self._close_popup()
                    return "ALL_LOCKED"

            elif popup == "LOCKED":
                # Governance already done, policies locked (need stages)
                self._close_popup()
                # Fall through to tap target policy below
                pass

        # ── Tap policies (dynamic position detection) ──
        y_list = self._get_tap_targets(col_idx, x_center)

        for pos_key, y in y_list:
            _log(f"Col {col_idx}: tap [{pos_key}] ({x_center}, {y})")
            adb_helper.tap(self.serial, x_center, y)
            time.sleep(2)

            popup = detect_policy_popup(self.serial, self.detector)
            _log(f"  Popup: {popup}")

            if popup == "ENACT":
                _log("  >>> ENACTING target policy!")
                success = _tap_policy_enact(self.serial, self.detector)
                if not success or not self._post_enact_check():
                    self._close_popup()
                    return "ALL_LOCKED"  # REPLENISH or ENACT failed
                self._close_popup()
                save_progress(col_idx, self.account_id)
                return "TARGET_ENACTED"

            elif popup == "REQUIREMENTS_GO":
                _log("  Has GO → following prerequisite chain...")
                result = self._follow_go_chain()

                if result == "ENACT_SUCCESS":
                    _log("  Prerequisite enacted! (progress NOT updated)")
                    return "ENACT_SUCCESS"

                elif result == "SELECT":
                    _log("  Hit governance in GO chain — selecting card 0")
                    card_pos = GOVERNANCE_CARD_POSITIONS[0]
                    adb_helper.tap(self.serial, card_pos[0], card_pos[1])
                    time.sleep(1.5)
                    SELECT_BTN = (480, 415)
                    adb_helper.tap(self.serial, SELECT_BTN[0], SELECT_BTN[1])
                    time.sleep(2)
                    self._close_popup()
                    return "GOVERNANCE_DONE"

                else:
                    self._close_popup()
                    # Try next position in tap_order
                    continue

            elif popup == "SELECT":
                handled = self._handle_governance(col_idx)
                if handled:
                    save_progress(col_idx, self.account_id)
                    return "GOVERNANCE_DONE"
                # Try next position
                self._close_popup()
                continue

            else:  # LOCKED
                self._close_popup()
                _log(f"  [{pos_key}] LOCKED — trying next position...")
                continue

        # All positions tried, all locked
        # Check fallback: if col has fallback_col, go back
        fallback = col.get("fallback_col")
        if fallback is not None and fallback < start_col:
            _log(f"  All LOCKED → fallback to col {fallback} (governance branches not complete)")
            save_progress(fallback - 1, self.account_id)  # Reset progress before fallback col
            return "ALL_LOCKED"

        _log(f"  Col {col_idx} all positions LOCKED")
        return "ALL_LOCKED"

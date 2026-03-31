"""
Game State Detector — Production-grade template matching engine.

Loads templates into RAM once and uses ADB screencap-to-memory for zero disk I/O.

Optimizations:
- Grayscale matching: 3x faster than color (1 channel vs 3)
- ROI cropping: scan only relevant screen region per template
- Early exit cache: check last matched state first (~90% hit rate)
- Screenshot cache: skip ADB if last capture < max_age_ms
- Unified template loader + single _find_template engine (DRY)
"""

import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ── Module Constants ──────────────────────────────────────────────

SCREEN_RESOLUTION = (960, 540)
SCREENCAP_TIMEOUT_SEC = 5
SCREEN_CACHE_MAX_AGE_MS = 100

UNKNOWN_STATE = "UNKNOWN / TRANSITION"
ERROR_CAPTURE = "ERROR_CAPTURE"

# Default thresholds per category (can be overridden per-call)
DEFAULT_THRESHOLDS = {
    "state": 0.80,
    "construction": 0.80,
    "special": 0.80,
    "activity": 0.98,
    "alliance": 0.98,
    "icon": 0.80,
    "account": 0.95,
}

# ── Type Aliases ──────────────────────────────────────────────────

TemplateEntry = dict          # {"color": np.ndarray, "gray": np.ndarray, "roi": tuple|None}
TemplateDict = dict           # {name: list[TemplateEntry]}
MatchResult = tuple           # (name, center_x, center_y)

# ── Template Configs & ROI (imported from detector_configs.py) ────
from backend.core.workflow.detector_configs import (  # noqa: E402
    STATE_CONFIGS,
    CONSTRUCTION_CONFIGS,
    SPECIAL_CONFIGS,
    ACTIVITY_CONFIGS,
    ALLIANCE_CONFIGS,
    ICON_CONFIGS,
    ACCOUNT_CONFIGS,
    ROI_HINTS,
    CATEGORY_REGISTRY as _CATEGORY_REGISTRY,
    STATE_PRIORITY as _STATE_PRIORITY,
    STATE_BASE as _STATE_BASE,
)


# ── Screen Cache ──────────────────────────────────────────────────

NEAR_MISS_MARGIN = 0.15  # Warn when confidence is within this margin below threshold


@dataclass
class _ScreenCache:
    """Cached ADB screenshot with grayscale pre-computation."""
    frame: Optional[np.ndarray] = None
    gray: Optional[np.ndarray] = None
    timestamp_ms: float = 0.0
    max_age_ms: float = SCREEN_CACHE_MAX_AGE_MS

    @property
    def is_fresh(self) -> bool:
        return self.frame is not None and (time.time() * 1000 - self.timestamp_ms) < self.max_age_ms

    def update(self, frame: np.ndarray) -> None:
        self.frame = frame
        self.gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame is not None else None
        self.timestamp_ms = time.time() * 1000

    def invalidate(self) -> None:
        self.frame = None
        self.gray = None
        self.timestamp_ms = 0.0


@dataclass
class _DiagEntry:
    """Single diagnostic record for one detection call."""
    caller: str             # e.g. "check_activity", "check_state"
    target: str             # template name tested
    confidence: float       # max_val from matchTemplate
    threshold: float        # threshold used
    time_ms: float          # elapsed time for this match
    matched: bool           # did it pass threshold?
    use_color: bool = False # gray or color matching


# ── Main Class ────────────────────────────────────────────────────

class GameStateDetector:
    """
    Modular State Detector — production-grade template matching engine.

    Usage:
        detector = GameStateDetector(adb_path, templates_dir)
        state = detector.check_state(serial)
        match = detector.check_activity(serial, target="CREATE_LEGION")
    """

    def __init__(self, adb_path: str, templates_dir: str) -> None:
        self.adb_path = adb_path
        self.templates_dir = templates_dir
        self.roi_hints = ROI_HINTS

        # Consolidated template registry: {category: {name: [TemplateEntry]}}
        self._registry: dict[str, TemplateDict] = {}
        self._last_matched_state: Optional[str] = None
        self._cache = _ScreenCache()

        # Diagnostic instrumentation
        self.diagnostic_mode: bool = False
        self._diag_log: list[_DiagEntry] = []

        self._load_all_templates()

    # ── Backward-compatible properties (zero breaking changes) ────

    @property
    def templates(self) -> TemplateDict:
        return self._registry.get("state", {})

    @property
    def construction_templates(self) -> TemplateDict:
        return self._registry.get("construction", {})

    @property
    def special_templates(self) -> TemplateDict:
        return self._registry.get("special", {})

    @property
    def activity_templates(self) -> TemplateDict:
        return self._registry.get("activity", {})

    @property
    def alliance_templates(self) -> TemplateDict:
        return self._registry.get("alliance", {})

    @property
    def icon_templates(self) -> TemplateDict:
        return self._registry.get("icon", {})

    @property
    def account_templates(self) -> TemplateDict:
        return self._registry.get("account", {})

    # Backward-compat: old cache attributes used by test files
    @property
    def _screen_cache(self):
        return self._cache.frame

    @_screen_cache.setter
    def _screen_cache(self, value):
        if value is None:
            self._cache.invalidate()
        else:
            self._cache.frame = value

    @property
    def _screen_gray_cache(self):
        return self._cache.gray

    @_screen_gray_cache.setter
    def _screen_gray_cache(self, value):
        self._cache.gray = value

    @property
    def _screen_cache_time(self):
        return self._cache.timestamp_ms

    @_screen_cache_time.setter
    def _screen_cache_time(self, value):
        self._cache.timestamp_ms = value

    # Keep old config attributes accessible for external tools
    @property
    def state_configs(self) -> dict:
        return STATE_CONFIGS

    @property
    def construction_configs(self) -> dict:
        return CONSTRUCTION_CONFIGS

    @property
    def special_configs(self) -> dict:
        return SPECIAL_CONFIGS

    @property
    def activity_configs(self) -> dict:
        return ACTIVITY_CONFIGS

    @property
    def alliance_configs(self) -> dict:
        return ALLIANCE_CONFIGS

    @property
    def icon_configs(self) -> dict:
        return ICON_CONFIGS

    @property
    def account_configs(self) -> dict:
        return ACCOUNT_CONFIGS

    # ── Template Loading ──────────────────────────────────────────

    def _load_template_group(self, configs: dict, target_dict: TemplateDict, label: str) -> None:
        """Load one category of templates into target_dict. Stores color + gray + ROI."""
        loaded = 0
        for filename, name in configs.items():
            path = os.path.join(self.templates_dir, filename)
            if not os.path.exists(path):
                logger.warning("%s template missing: %s", label, path)
                continue

            img = cv2.imread(path, cv2.IMREAD_COLOR)
            if img is None:
                logger.error("Failed to load: %s", path)
                continue

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            roi = self.roi_hints.get(filename)

            target_dict.setdefault(name, []).append({
                "color": img,
                "gray": gray,
                "roi": roi,
            })
            loaded += 1

        if loaded > 0:
            logger.info("Loaded %d %s templates.", loaded, label)

    def _load_all_templates(self) -> None:
        """Load all template categories into the unified registry."""
        logger.info("Pre-loading image templates into RAM...")
        for category, configs in _CATEGORY_REGISTRY.items():
            self._registry[category] = {}
            self._load_template_group(configs, self._registry[category], category.capitalize())
        logger.info("Template loading complete.")

    # ── Screencap ─────────────────────────────────────────────────

    def screencap_memory(self, serial: str) -> Optional[np.ndarray]:
        """Capture screen directly to RAM with caching."""
        if self._cache.is_fresh:
            return self._cache.frame

        cmd = [self.adb_path, "-s", serial, "exec-out", "screencap", "-p"]
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        try:
            result = subprocess.run(cmd, capture_output=True, startupinfo=startupinfo, timeout=SCREENCAP_TIMEOUT_SEC)
            if not result.stdout:
                stderr_text = (result.stderr or b"").decode("utf-8", errors="ignore").strip()
                logger.warning(
                    "Screencap empty on %s | returncode=%s | stderr=%s",
                    serial,
                    result.returncode,
                    stderr_text[:240] or "<empty>",
                )
                return None

            image_array = np.frombuffer(result.stdout, np.uint8)
            img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            if img is None:
                stderr_text = (result.stderr or b"").decode("utf-8", errors="ignore").strip()
                logger.warning(
                    "Screencap decode failed on %s | bytes=%d | returncode=%s | stderr=%s",
                    serial,
                    len(result.stdout),
                    result.returncode,
                    stderr_text[:240] or "<empty>",
                )
                return None
            self._cache.update(img)
            return img
        except subprocess.TimeoutExpired:
            logger.warning("Screencap timeout on %s", serial)
            return None
        except Exception as e:
            logger.error("Screencap failed on %s: %s", serial, e)
            return None

    def _get_gray(self, screen: np.ndarray) -> np.ndarray:
        """Get grayscale version of screen, using cache if available."""
        if self._cache.frame is not None and screen is self._cache.frame and self._cache.gray is not None:
            return self._cache.gray
        return cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)

    # ── Core Matching Engine ──────────────────────────────────────

    def _match_single(
        self,
        screen_gray: np.ndarray,
        entry: TemplateEntry,
        threshold: float,
        use_color: bool = False,
        screen_color: Optional[np.ndarray] = None,
    ) -> tuple[float, tuple[int, int]]:
        """
        Match one template entry against screen.
        Returns (max_val, max_loc) with loc in absolute screen coordinates.
        """
        if use_color and screen_color is not None:
            tmpl = entry["color"]
            screen_src = screen_color
        else:
            tmpl = entry["gray"]
            screen_src = screen_gray

        roi = entry.get("roi")

        if roi:
            x1, y1, x2, y2 = roi
            region = screen_src[y1:y2, x1:x2]
            if region.shape[0] < tmpl.shape[0] or region.shape[1] < tmpl.shape[1]:
                region = screen_src
                roi = None
        else:
            region = screen_src

        if region.shape[0] < tmpl.shape[0] or region.shape[1] < tmpl.shape[1]:
            return 0.0, (0, 0)

        res = cv2.matchTemplate(region, tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if roi:
            max_loc = (max_loc[0] + roi[0], max_loc[1] + roi[1])

        return max_val, max_loc

    # ── Diagnostic Helpers ─────────────────────────────────────────

    def _record_diag(
        self, caller: str, target: str, confidence: float,
        threshold: float, time_ms: float, matched: bool, use_color: bool = False,
    ) -> None:
        """Record a diagnostic entry if diagnostic_mode is ON."""
        if not self.diagnostic_mode:
            return
        self._diag_log.append(_DiagEntry(
            caller=caller, target=target, confidence=confidence,
            threshold=threshold, time_ms=time_ms, matched=matched, use_color=use_color,
        ))

    # ── Unified Template Finder (DRY engine) ──────────────────────

    def _find_template(
        self,
        serial: str,
        template_dict: TemplateDict,
        target: Optional[str] = None,
        threshold: float = 0.80,
        use_color: bool = False,
        frame: Optional[np.ndarray] = None,
        _caller: str = "_find_template",
    ) -> Optional[MatchResult]:
        """
        Universal template finder — single engine replacing 6 duplicated methods.
        Returns (name, center_x, center_y) if found, or None.
        """
        screen = frame if frame is not None else self.screencap_memory(serial)
        if screen is None:
            return None

        if target and target not in template_dict:
            return None

        screen_gray = self._get_gray(screen)
        checks = {target: template_dict[target]} if target else template_dict

        for name, entries in checks.items():
            for entry in entries:
                t0 = time.perf_counter()
                max_val, max_loc = self._match_single(
                    screen_gray, entry, threshold,
                    use_color=use_color, screen_color=screen if use_color else None,
                )
                elapsed = (time.perf_counter() - t0) * 1000
                matched = max_val >= threshold
                self._record_diag(_caller, name, max_val, threshold, elapsed, matched, use_color)

                if matched:
                    h, w = entry["color"].shape[:2]
                    cx = max_loc[0] + w // 2
                    cy = max_loc[1] + h // 2
                    logger.debug("%s found at (%d, %d) | conf=%.3f", name, cx, cy, max_val)
                    return (name, cx, cy)

        return None

    def _find_name_only(
        self,
        screen: np.ndarray,
        template_dict: TemplateDict,
        target: Optional[str] = None,
        threshold: float = 0.80,
        _caller: str = "_find_name_only",
    ) -> Optional[str]:
        """Match templates and return only the name (no coordinates). Used by state/construction/special."""
        if target and target not in template_dict:
            return None

        screen_gray = self._get_gray(screen)
        checks = {target: template_dict[target]} if target else template_dict

        for name, entries in checks.items():
            for entry in entries:
                t0 = time.perf_counter()
                max_val, _ = self._match_single(screen_gray, entry, threshold)
                elapsed = (time.perf_counter() - t0) * 1000
                matched = max_val >= threshold
                self._record_diag(_caller, name, max_val, threshold, elapsed, matched)

                if matched:
                    return name
        return None

    # ── State Detection (unique logic — priority ordering + early exit cache) ──

    def _match_state_from_screen(self, screen: np.ndarray, threshold: float = 0.8) -> str:
        """Core state matching with early-exit cache + priority ordering."""
        screen_gray = self._get_gray(screen)
        state_dict = self.templates
        diag = self.diagnostic_mode

        def _check_entries(state_name: str) -> bool:
            for entry in state_dict[state_name]:
                t0 = time.perf_counter()
                max_val, _ = self._match_single(screen_gray, entry, threshold)
                elapsed = (time.perf_counter() - t0) * 1000
                matched = max_val >= threshold
                if diag:
                    self._record_diag("check_state", state_name, max_val, threshold, elapsed, matched)
                if matched:
                    return True
            return False

        # Early exit: try last matched state first (~90% hit rate in steady states)
        if self._last_matched_state and self._last_matched_state in state_dict:
            if _check_entries(self._last_matched_state):
                return self._last_matched_state

        # Priority scan
        for state_name in _STATE_PRIORITY:
            if state_name == self._last_matched_state:
                continue
            if state_name in state_dict:
                if _check_entries(state_name):
                    self._last_matched_state = state_name
                    return state_name

        # Base states
        for state_name in _STATE_BASE:
            if state_name == self._last_matched_state:
                continue
            if state_name in state_dict:
                if _check_entries(state_name):
                    self._last_matched_state = state_name
                    return state_name

        self._last_matched_state = None
        return UNKNOWN_STATE

    # ── Public API ────────────────────────────────────────────────

    def get_frame(self, serial: str) -> Optional[np.ndarray]:
        """Capture and return the current screen frame."""
        return self.screencap_memory(serial)

    def check_state(self, serial: str, threshold: float = 0.8) -> str:
        """Determines the current game state via template matching."""
        screen = self.screencap_memory(serial)
        if screen is None:
            return ERROR_CAPTURE
        return self._match_state_from_screen(screen, threshold)

    def check_state_full(self, serial: str, threshold: float = 0.8) -> dict:
        """Comprehensive state check. Single screencap, checks ALL categories."""
        screen = self.screencap_memory(serial)
        if screen is None:
            return {"state": ERROR_CAPTURE, "construction": None, "special": None, "screen": None}

        state = self._match_state_from_screen(screen, threshold)
        construction = None
        special = None

        if state == UNKNOWN_STATE:
            construction = self._find_name_only(screen, self.construction_templates, threshold=threshold)
            if not construction:
                special = self._find_name_only(screen, self.special_templates, threshold=threshold)

        return {"state": state, "construction": construction, "special": special, "screen": screen}

    def is_menu_expanded(self, serial: str, threshold: float = 0.8) -> bool:
        """Checks if the expandable lobby menu is currently open."""
        if "LOBBY_MENU_EXPANDED" not in self.templates:
            return False
        screen = self.screencap_memory(serial)
        if screen is None:
            return False
        screen_gray = self._get_gray(screen)
        for entry in self.templates["LOBBY_MENU_EXPANDED"]:
            max_val, _ = self._match_single(screen_gray, entry, threshold)
            if max_val >= threshold:
                return True
        return False

    def check_construction(self, serial: str, target: Optional[str] = None, threshold: float = 0.8) -> Optional[str]:
        """Checks for construction buildings. Returns matched name or None."""
        screen = self.screencap_memory(serial)
        if screen is None:
            return None
        return self._find_name_only(screen, self.construction_templates, target, threshold, _caller="check_construction")

    def check_special_state(
        self, serial: str, target: Optional[str] = None, threshold: float = 0.8, frame: Optional[np.ndarray] = None,
    ) -> Optional[str]:
        """Checks for special screens. Returns matched name or None."""
        screen = frame if frame is not None else self.screencap_memory(serial)
        if screen is None:
            return None
        return self._find_name_only(screen, self.special_templates, target, threshold, _caller="check_special_state")

    def check_activity(
        self, serial: str, target: Optional[str] = None, threshold: float = 0.8, frame: Optional[np.ndarray] = None,
    ) -> Optional[MatchResult]:
        """Activity Detector — returns (name, center_x, center_y) or None."""
        return self._find_template(serial, self.activity_templates, target, threshold, use_color=True, frame=frame, _caller="check_activity")

    def check_alliance(
        self, serial: str, target: Optional[str] = None, threshold: float = 0.9,
    ) -> Optional[MatchResult]:
        """Alliance Detector — returns (name, center_x, center_y) or None."""
        return self._find_template(serial, self.alliance_templates, target, threshold, use_color=True, _caller="check_alliance")

    def locate_icon(
        self, serial: str, target: Optional[str] = None, threshold: float = 0.8,
    ) -> Optional[MatchResult]:
        """Icon/Marker Detector — returns (name, center_x, center_y) or None."""
        return self._find_template(serial, self.icon_templates, target, threshold, use_color=True, _caller="locate_icon")

    def check_account_state(
        self, serial: str, target: Optional[str] = None, threshold: float = 0.95,
    ) -> Optional[MatchResult]:
        """Account Detector — returns (name, center_x, center_y) or None."""
        return self._find_template(serial, self.account_templates, target, threshold, use_color=True, _caller="check_account_state")

    def find_all_activity_matches(self, serial: str, target: str, threshold: float = 0.8) -> list[tuple[int, int]]:
        """
        Multi-match activity detector with Non-Maximum Suppression.
        Returns ALL matching positions sorted top-to-bottom.
        """
        screen = self.screencap_memory(serial)
        if screen is None:
            return []
        screen_gray = self._get_gray(screen)

        if target not in self.activity_templates:
            logger.warning("Target '%s' not found in activity_templates.", target)
            return []

        results: list[tuple[int, int]] = []

        for entry in self.activity_templates[target]:
            tmpl_gray = entry["gray"]
            roi = entry.get("roi")

            if roi:
                x1, y1, x2, y2 = roi
                region = screen_gray[y1:y2, x1:x2]
                if region.shape[0] < tmpl_gray.shape[0] or region.shape[1] < tmpl_gray.shape[1]:
                    region = screen_gray
                    roi = None
            else:
                region = screen_gray

            res = cv2.matchTemplate(region, tmpl_gray, cv2.TM_CCOEFF_NORMED)
            h, w = tmpl_gray.shape[:2]

            while True:
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                if max_val < threshold:
                    break

                offset_x = roi[0] if roi else 0
                offset_y = roi[1] if roi else 0
                results.append((offset_x + max_loc[0] + w // 2, offset_y + max_loc[1] + h // 2))

                # NMS — suppress this match region
                sx = max(0, max_loc[0] - w // 2)
                sy = max(0, max_loc[1] - h // 2)
                ex = min(res.shape[1], max_loc[0] + w // 2 + 1)
                ey = min(res.shape[0], max_loc[1] + h // 2 + 1)
                res[sy:ey, sx:ex] = 0

        results.sort(key=lambda p: p[1])
        if results:
            logger.debug("Multi-match '%s': %d match(es) at %s", target, len(results), results)
        return results

    # ── Diagnostic API ────────────────────────────────────────────

    def clear_diagnostics(self) -> None:
        """Clear all recorded diagnostic entries."""
        self._diag_log.clear()

    def get_diagnostics(self) -> list[_DiagEntry]:
        """Return raw diagnostic log entries."""
        return list(self._diag_log)

    def print_diagnostics(self, show_all: bool = False) -> None:
        """
        Print formatted diagnostic report to console.

        Args:
            show_all: If True, show every match attempt. If False (default),
                      show only matches + near-misses.
        """
        if not self._diag_log:
            print("[DIAG] No diagnostic entries recorded. Set detector.diagnostic_mode = True first.")
            return

        matches = [e for e in self._diag_log if e.matched]
        near_misses = [
            e for e in self._diag_log
            if not e.matched and e.confidence >= (e.threshold - NEAR_MISS_MARGIN)
        ]
        total_time = sum(e.time_ms for e in self._diag_log)
        slowest = max(self._diag_log, key=lambda e: e.time_ms) if self._diag_log else None

        print(f"\n{'═' * 80}")
        print(f"  DIAGNOSTIC REPORT — {len(self._diag_log)} calls recorded")
        print(f"{'═' * 80}")

        # Group by caller for cleaner output
        callers_seen: dict[str, list[_DiagEntry]] = {}
        for e in self._diag_log:
            callers_seen.setdefault(e.caller, []).append(e)

        for caller, entries in callers_seen.items():
            caller_matches = sum(1 for e in entries if e.matched)
            caller_time = sum(e.time_ms for e in entries)
            print(f"\n── {caller}() — {len(entries)} attempts, {caller_matches} matched, {caller_time:.1f}ms total ──")

            for e in entries:
                if not show_all and not e.matched and e.confidence < (e.threshold - NEAR_MISS_MARGIN):
                    continue  # Skip low-confidence misses in compact mode

                marker = "✓" if e.matched else ("⚠" if e.confidence >= (e.threshold - NEAR_MISS_MARGIN) else "·")
                color_tag = "COLOR" if e.use_color else "GRAY "
                print(
                    f"  {marker} {e.target:<40} "
                    f"conf={e.confidence:.4f} thr={e.threshold:.2f} "
                    f"{color_tag} {e.time_ms:>6.1f}ms"
                )

        # Summary
        print(f"\n{'─' * 80}")
        print(f"  SUMMARY")
        print(f"    Total calls:  {len(self._diag_log)}")
        print(f"    Matches:      {len(matches)}")
        print(f"    Near-misses:  {len(near_misses)}")
        print(f"    Total time:   {total_time:.1f}ms")
        if slowest:
            print(f"    Slowest:      {slowest.caller}() → {slowest.target} ({slowest.time_ms:.1f}ms)")

        # Near-miss warnings
        if near_misses:
            print(f"\n  ⚠ NEAR-MISS WARNINGS (confidence within {NEAR_MISS_MARGIN} of threshold):")
            for e in near_misses:
                gap = e.threshold - e.confidence
                print(
                    f"    {e.caller}() → {e.target}: "
                    f"conf={e.confidence:.4f} (threshold={e.threshold:.2f}, gap={gap:.4f})"
                )
            print(f"    → Consider lowering threshold or improving template quality.")

        print(f"{'═' * 80}\n")

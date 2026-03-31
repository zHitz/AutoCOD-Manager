"""Runtime log and local-save probing for PET SANCTUARY true-parameter research."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

try:
    from .config import ResearchConfig
except ImportError:  # pragma: no cover - direct script execution fallback
    from config import ResearchConfig


ERROR_RUNTIME_LOG_NOT_ACCESSIBLE = "RUNTIME_LOG_NOT_ACCESSIBLE"
ERROR_TRUE_PARAMETER_SOURCE_NOT_FOUND = "TRUE_PARAMETER_SOURCE_NOT_FOUND"

PACKAGE_NAME = "com.farlightgames.samo.gp.vn"
APP_FILES_DIR = f"/sdcard/Android/data/{PACKAGE_NAME}/files"
PARK_LOG_DIR = f"{APP_FILES_DIR}/park/log"
DOC_DIR = f"{APP_FILES_DIR}/GLGData/com_farlightgames_samo_gp_vn/doc"

_ROLE_ID_RE = re.compile(r"roleId[:=](\d+)")
_JSON_RESPONSE_RE = re.compile(r"parseData v2 = (?P<endpoint>[^,]+), response = (?P<json>\{.*\})")
_HTTP_URL_RE = re.compile(r"https?://\S+")
_PRINTABLE_ASCII_RE = re.compile(rb"[ -~]{4,}")
_PRINTABLE_UTF16_RE = re.compile(r"[A-Za-z0-9_ /:@.-]{4,}")
_DOC_LISTING_RE = re.compile(
    r"^[\-dl][rwx\-]{9}\s+\d+\s+\S+\s+\S+\s+(?P<size>\d+)\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\s+(?P<name>.+)$"
)
_HINT_KEYWORDS = (
    "pet",
    "sanctuary",
    "token",
    "inventory",
    "item",
    "resource",
    "currency",
    "role",
)


def _build_startupinfo():
    if not hasattr(subprocess, "STARTUPINFO"):
        return None
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return startupinfo


def _extract_role_id(text: str) -> int | None:
    matches = _ROLE_ID_RE.findall(text or "")
    if not matches:
        return None
    return int(matches[-1])


def _extract_printable_strings(data: bytes) -> list[str]:
    ascii_strings = [match.decode("latin1", errors="ignore") for match in _PRINTABLE_ASCII_RE.findall(data)]
    utf16_strings: list[str] = []
    try:
        utf16_text = data.decode("utf-16le", errors="ignore")
    except Exception:
        utf16_text = ""
    if utf16_text:
        utf16_strings = _PRINTABLE_UTF16_RE.findall(utf16_text)

    seen: set[str] = set()
    merged: list[str] = []
    for value in ascii_strings + utf16_strings:
        compact = value.strip()
        if not compact or compact in seen:
            continue
        seen.add(compact)
        merged.append(compact)
    return merged[:60]


def _extract_json_responses(text: str) -> list[dict]:
    responses: list[dict] = []
    for line in text.splitlines():
        match = _JSON_RESPONSE_RE.search(line)
        if not match:
            continue
        endpoint = match.group("endpoint").strip()
        raw_json = match.group("json").strip()
        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError:
            responses.append({"endpoint": endpoint, "raw_json": raw_json, "json_error": True})
            continue
        responses.append({"endpoint": endpoint, "payload": payload})
    return responses


def _iter_key_values(value, prefix: str = ""):
    if isinstance(value, dict):
        for key, item in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            yield child_prefix, item
            yield from _iter_key_values(item, child_prefix)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            child_prefix = f"{prefix}[{index}]"
            yield from _iter_key_values(item, child_prefix)


def _find_pet_token_candidates(responses: list[dict]) -> list[dict]:
    candidates: list[dict] = []
    for entry in responses:
        payload = entry.get("payload")
        if not isinstance(payload, dict):
            continue
        for path, value in _iter_key_values(payload):
            key_name = path.split(".")[-1].lower()
            normalized = key_name.replace("[", "").replace("]", "").replace("_", "")
            if "pet" not in normalized or "token" not in normalized:
                continue
            if isinstance(value, bool):
                continue
            if isinstance(value, int):
                candidates.append(
                    {"endpoint": entry["endpoint"], "path": path, "value": value, "source": "json_response"}
                )
    return candidates


def _find_role_file_pet_token_candidates(role_files: list[dict]) -> list[dict]:
    candidates: list[dict] = []
    for entry in role_files:
        strings = entry.get("printable_strings") or []
        for index, value in enumerate(strings):
            normalized = str(value).lower().replace("_", "")
            if "pet" not in normalized or "token" not in normalized:
                continue
            for look_ahead in strings[index + 1 : index + 4]:
                compact = str(look_ahead).replace(",", "").strip()
                if compact.isdigit():
                    candidates.append(
                        {
                            "file": entry.get("name"),
                            "path": f"{entry.get('name')}[{index + 1}]",
                            "value": int(compact),
                            "source": "role_file_printable_strings",
                        }
                    )
                    break
    return candidates


def _parse_doc_listing(doc_listing: str) -> list[dict]:
    entries: list[dict] = []
    for line in doc_listing.splitlines():
        match = _DOC_LISTING_RE.match(line.strip())
        if not match:
            continue
        entries.append({"name": match.group("name"), "size": int(match.group("size"))})
    return entries


class RuntimeLogProbe:
    """Probe runtime-accessible logs and local files for true parameters."""

    def __init__(self, settings: ResearchConfig):
        self.settings = settings
        self._startupinfo = _build_startupinfo()

    def _run(self, *adb_args: str, timeout: int = 20, text: bool = True):
        cmd = [self.settings.adb_path, "-s", self.settings.serial, *adb_args]
        return subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout,
            text=text,
            startupinfo=self._startupinfo,
            encoding="utf-8" if text else None,
            errors="replace" if text else None,
        )

    def _shell_text_args(self, *adb_args: str, timeout: int = 20) -> tuple[bool, str]:
        try:
            result = self._run("shell", *adb_args, timeout=timeout, text=True)
        except subprocess.TimeoutExpired:
            return False, "shell command timed out"
        output = (result.stdout or "") + (result.stderr or "")
        return result.returncode == 0, output.strip()

    def _shell_bytes_args(self, *adb_args: str, timeout: int = 20) -> tuple[bool, bytes]:
        try:
            result = self._run("shell", *adb_args, timeout=timeout, text=False)
        except subprocess.TimeoutExpired:
            return False, b""
        return result.returncode == 0, result.stdout or b""

    def _latest_park_log_path(self) -> tuple[bool, str]:
        ok, output = self._shell_text_args("ls", "-1", PARK_LOG_DIR, timeout=20)
        if not ok:
            return False, output
        entries = [line.strip() for line in output.splitlines() if line.strip()]
        if not entries:
            return False, ""
        dated_entries = sorted(
            [entry for entry in entries if re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry)],
            reverse=True,
        )
        if dated_entries:
            return True, dated_entries[0]
        return True, sorted(entries, reverse=True)[0]

    def _read_latest_park_log(self) -> tuple[bool, str, str | None]:
        ok, latest_name = self._latest_park_log_path()
        if not ok or not latest_name:
            return False, "", None
        remote_path = f"{PARK_LOG_DIR}/{latest_name.splitlines()[0].strip()}"
        ok, text = self._shell_text_args("tail", "-n", "400", remote_path, timeout=30)
        if not ok:
            return False, text, remote_path
        return True, text, remote_path

    def _list_recent_doc_files(self) -> tuple[bool, str]:
        return self._shell_text_args("ls", "-lt", DOC_DIR, timeout=30)

    def _read_logcat(self) -> tuple[bool, str]:
        try:
            result = self._run("logcat", "-d", "-t", "1500", timeout=30, text=True)
        except subprocess.TimeoutExpired:
            return False, "logcat timed out"
        output = (result.stdout or "") + (result.stderr or "")
        return result.returncode == 0, output.strip()

    def _read_small_role_files(self, role_id: int | None, run_dir: Path) -> list[dict]:
        if not role_id:
            return []

        candidates = [
            f"Mark_{role_id}",
            f"KingdomOverviewSave{role_id}",
            f"SearchData_{role_id}",
            f"QuestSave{role_id}",
            f"BPQuestSave{role_id}",
            f"IAPLocalSave_{role_id}",
            f"RedDotServerDataMap2_{role_id}",
            f"RedDotServerDataMap3_{role_id}",
            f"RedDotServerDataMap4_{role_id}",
            f"RedDotServerDataMap5_{role_id}",
            f"RedDotServerDataMap6_{role_id}",
            f"RedDotServerDataMap8_{role_id}",
        ]
        files_dir = run_dir / "role_files"
        files_dir.mkdir(parents=True, exist_ok=True)

        details: list[dict] = []
        for name in candidates:
            remote_path = f"{DOC_DIR}/{name}"
            ok, data = self._shell_bytes_args("cat", remote_path, timeout=20)
            if not ok or not data:
                continue
            local_path = files_dir / name
            local_path.write_bytes(data)
            details.append(
                {
                    "name": name,
                    "remote_path": remote_path,
                    "local_path": str(local_path.resolve()),
                    "size": len(data),
                    "printable_strings": _extract_printable_strings(data),
                }
            )
        return details

    def _read_recent_small_doc_files(
        self,
        doc_entries: list[dict],
        run_dir: Path,
        *,
        exclude_names: set[str] | None = None,
        max_files: int = 12,
    ) -> list[dict]:
        exclude_names = exclude_names or set()
        files_dir = run_dir / "recent_doc_files"
        files_dir.mkdir(parents=True, exist_ok=True)

        details: list[dict] = []
        for entry in doc_entries:
            name = entry["name"]
            if name in exclude_names:
                continue
            if entry["size"] <= 0 or entry["size"] > 4096:
                continue
            if "." in name and not name.lower().endswith(".txt"):
                continue
            remote_path = f"{DOC_DIR}/{name}"
            ok, data = self._shell_bytes_args("cat", remote_path, timeout=20)
            if not ok or not data:
                continue
            local_path = files_dir / name
            local_path.write_bytes(data)
            details.append(
                {
                    "name": name,
                    "remote_path": remote_path,
                    "local_path": str(local_path.resolve()),
                    "size": len(data),
                    "printable_strings": _extract_printable_strings(data),
                }
            )
            if len(details) >= max_files:
                break
        return details

    def collect(self, run_dir: Path) -> dict:
        park_log_ok, park_log_text, remote_park_log = self._read_latest_park_log()
        doc_ok, doc_listing = self._list_recent_doc_files()
        logcat_ok, logcat_text = self._read_logcat()

        if not park_log_ok and not doc_ok and not logcat_ok:
            return {
                "ok": False,
                "method": "runtime_log_probe",
                "screen": "PET_SANCTUARY",
                "pet_token": None,
                "error": ERROR_RUNTIME_LOG_NOT_ACCESSIBLE,
                "diagnostics": {
                    "remote_park_log": remote_park_log,
                    "park_log_error": park_log_text,
                    "doc_listing_error": doc_listing,
                    "logcat_error": logcat_text,
                },
            }

        park_log_path = run_dir / "park_log_tail.txt"
        doc_listing_path = run_dir / "doc_listing.txt"
        logcat_path = run_dir / "logcat_tail.txt"
        if park_log_text:
            park_log_path.write_text(park_log_text, encoding="utf-8")
        if doc_listing:
            doc_listing_path.write_text(doc_listing, encoding="utf-8")
        if logcat_text:
            logcat_path.write_text(logcat_text, encoding="utf-8")

        role_id = _extract_role_id(park_log_text)
        if role_id is None:
            role_matches = re.findall(r"(?:_|Save)(\d{6,})", doc_listing)
            if role_matches:
                role_id = int(role_matches[0])
        doc_entries = _parse_doc_listing(doc_listing)
        role_files = self._read_small_role_files(role_id, run_dir)
        recent_doc_files = self._read_recent_small_doc_files(
            doc_entries,
            run_dir,
            exclude_names={entry["name"] for entry in role_files},
        )
        responses = _extract_json_responses(park_log_text)
        token_candidates = _find_pet_token_candidates(responses)
        token_candidates.extend(_find_role_file_pet_token_candidates(role_files))
        token_candidates.extend(_find_role_file_pet_token_candidates(recent_doc_files))

        interesting_lines = [
            line
            for line in park_log_text.splitlines()
            if any(keyword in line.lower() for keyword in _HINT_KEYWORDS)
        ][-80:]
        urls = []
        for line in park_log_text.splitlines():
            urls.extend(_HTTP_URL_RE.findall(line))
        logcat_interesting = [
            line
            for line in logcat_text.splitlines()
            if PACKAGE_NAME in line or any(keyword in line.lower() for keyword in _HINT_KEYWORDS)
        ][-120:]

        diagnostics = {
            "remote_park_log": remote_park_log,
            "park_log_tail_path": str(park_log_path.resolve()) if park_log_text else None,
            "doc_listing_path": str(doc_listing_path.resolve()) if doc_listing else None,
            "logcat_tail_path": str(logcat_path.resolve()) if logcat_text else None,
            "role_id": role_id,
            "interesting_lines": interesting_lines,
            "logcat_interesting_lines": logcat_interesting,
            "json_response_count": len(responses),
            "json_response_endpoints": [entry.get("endpoint") for entry in responses[:30]],
            "http_urls": list(dict.fromkeys(urls))[:40],
            "token_candidates": token_candidates,
            "role_files": role_files,
            "recent_doc_files": recent_doc_files,
            "candidate_sources": [
                "park/log contains structured network and SDK responses accessible without root",
                "GLGData/doc contains role-scoped local save/cache files accessible from shared storage",
            ],
        }

        if token_candidates:
            best = token_candidates[-1]
            return {
                "ok": True,
                "method": "runtime_log_probe",
                "screen": "PET_SANCTUARY",
                "pet_token": int(best["value"]),
                "error": None,
                "diagnostics": diagnostics,
            }

        return {
            "ok": False,
            "method": "runtime_log_probe",
            "screen": "PET_SANCTUARY",
            "pet_token": None,
            "error": ERROR_TRUE_PARAMETER_SOURCE_NOT_FOUND,
            "diagnostics": diagnostics,
        }

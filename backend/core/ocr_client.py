"""
OCR API Client — ocrapi.cloud integration with key rotation.

Pipeline: upload PDF -> poll job status -> download markdown result -> parse.
"""

import re
import time
import itertools
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from backend.config import config

BASE_URL = "https://ocrapi.cloud/api/v1"
POLL_INTERVAL = 3
MAX_POLL_ATTEMPTS = 60


# ── API Key Gateway ──


def load_api_keys() -> list[str]:
    """Load API keys from config file (one per line, # = comment)."""
    keys_file = config.get_api_keys_path()

    if not keys_file.exists():
        print(f"[OCR] Warning: API keys file not found: {keys_file}")
        return []

    keys = []
    with open(keys_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                keys.append(line)
    print(f"[OCR] Loaded {len(keys)} API key(s)")
    return keys


class KeyGateway:
    """Round-robin API key manager."""

    def __init__(self, keys: list[str]):
        self._keys = keys
        self._cycle = itertools.cycle(keys) if keys else None
        self._current = next(self._cycle) if self._cycle else ""

    def current_key(self) -> str:
        return self._current

    def rotate(self) -> str:
        if self._cycle:
            self._current = next(self._cycle)
            print(f"  [OCR] Rotated to key ...{self._current[-6:]}")
        return self._current

    def auth_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._current}",
            "User-Agent": "COD-Manager/1.0",
        }


# ── HTTP Session ──


def build_session() -> requests.Session:
    retry = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["POST", "GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# ── Core API Operations ──


def submit_job(
    session: requests.Session, gateway: KeyGateway, file_path: str
) -> str | None:
    """Upload file and create OCR job. Returns job_id."""
    url = f"{BASE_URL}/jobs"
    data = {
        "file_format": "pdf",
        "language": "en",
        "extract_tables": "true",
        "webhook_events": "job.completed job.failed",
    }

    for _ in range(10):
        with open(file_path, "rb") as fobj:
            resp = session.post(
                url,
                headers=gateway.auth_headers(),
                files={"file_upload": fobj},
                data=data,
                timeout=60,
            )
        if resp.status_code == 429:
            gateway.rotate()
            time.sleep(1)
            continue
        if resp.status_code not in (200, 201, 202):
            print(f"  [OCR] API Error {resp.status_code}: {resp.text}")
            return None
        job = resp.json()
        job_id = job.get("job_id")
        print(f"  [OCR] Job submitted: {job_id}")
        return job_id

    return None


def poll_job(
    session: requests.Session, gateway: KeyGateway, job_id: str
) -> dict | None:
    """Poll until job completes. Returns job dict or None."""
    url = f"{BASE_URL}/jobs/{job_id}"

    for attempt in range(1, MAX_POLL_ATTEMPTS + 1):
        try:
            resp = session.get(url, headers=gateway.auth_headers(), timeout=30)
            if resp.status_code == 429:
                gateway.rotate()
                time.sleep(1)
                continue
            resp.raise_for_status()
            job = resp.json()
        except requests.RequestException as e:
            print(f"  [OCR] Poll error: {e}")
            time.sleep(POLL_INTERVAL)
            continue

        status = job.get("status", "")
        print(f"  [OCR] Poll {attempt}/{MAX_POLL_ATTEMPTS}: {status}")

        if status == "completed":
            return job
        if status in ("failed", "cancelled"):
            print(f"  [OCR] Job {status}: {job.get('error', 'unknown')}")
            return None
        time.sleep(POLL_INTERVAL)

    print("  [OCR] Timeout waiting for job completion")
    return None


def extract_text(job: dict) -> str:
    """Extract markdown text from completed job."""
    pages = job.get("pages", [])
    parts = []
    for page in pages:
        text = page.get("results", {}).get("text", "")
        if text:
            parts.append(text)
    return "\n\n".join(parts)


# ── Markdown Parser ──


def _parse_resource_value(text: str) -> int:
    """Parse values like '589.7M', '1.2B', '500K', '13,572' to int."""
    text = text.strip().replace(",", "")
    multiplier = 1
    if text.upper().endswith("B"):
        multiplier = 1_000_000_000
        text = text[:-1]
    elif text.upper().endswith("M"):
        multiplier = 1_000_000
        text = text[:-1]
    elif text.upper().endswith("K"):
        multiplier = 1_000
        text = text[:-1]
    try:
        return int(float(text) * multiplier)
    except (ValueError, TypeError):
        return 0


def parse_scan_markdown(md_text: str) -> dict:
    """Parse OCR markdown output into structured data.

    Expected format:
        Gold
        296.8M     <- current (ignore)
        589.7M     <- total (KEEP)
        Wood/Ore/Mana same pattern
        Lord
        dragonball Goten
        Power
        14,837,914
        Merits
        7,111
        HALLOFORDER
        Level23
        BAZAAR
        Level23
        13,572     <- pet_token (last number)
    """
    lines = [l.strip() for l in md_text.strip().splitlines() if l.strip()]

    result = {
        "lord_name": "",
        "power": 0,
        "hall_level": 0,
        "market_level": 0,
        "pet_token": 0,
        "resources": {"gold": 0, "wood": 0, "ore": 0, "mana": 0},
    }

    # Resource parsing: find resource names and take the 2nd value after each
    resource_names = ["gold", "wood", "ore", "mana"]
    i = 0
    while i < len(lines):
        line_lower = lines[i].lower()

        # Resources: name -> skip 1st value -> take 2nd value
        for res_name in resource_names:
            if line_lower == res_name:
                # Next 2 lines should be: current (skip), total (keep)
                if i + 2 < len(lines):
                    result["resources"][res_name] = _parse_resource_value(lines[i + 2])
                    i += 2
                break

        # Lord name (may span multiple lines if special chars cause height diff)
        if line_lower == "lord":
            name_parts = []
            j = i + 1
            while j < len(lines) and lines[j].lower() not in ("power", "merits"):
                name_parts.append(lines[j])
                j += 1
            if name_parts:
                result["lord_name"] = " ".join(name_parts)
                i = j - 1  # will be incremented by outer loop

        # Power
        elif line_lower == "power":
            if i + 1 < len(lines):
                result["power"] = _parse_resource_value(lines[i + 1])
                i += 1

        # Hall level
        elif "halloforder" in line_lower or "hall" in line_lower:
            if i + 1 < len(lines):
                match = re.search(r"(\d+)", lines[i + 1])
                if match:
                    result["hall_level"] = int(match.group(1))
                    i += 1

        # Market level (Bazaar)
        elif "bazaar" in line_lower or "market" in line_lower:
            if i + 1 < len(lines):
                match = re.search(r"(\d+)", lines[i + 1])
                if match:
                    result["market_level"] = int(match.group(1))
                    i += 1

        i += 1

    # Pet token: last numeric value in the text
    for line in reversed(lines):
        val = _parse_resource_value(line)
        if val > 0:
            result["pet_token"] = val
            break

    return result


# ── High-level OCR Function ──


def run_ocr(pdf_path: str) -> dict:
    """Run full OCR pipeline on a PDF file.

    Returns: {"success": bool, "text": str, "parsed": dict, "error": str}
    """
    keys = load_api_keys()
    if not keys:
        return {
            "success": False,
            "error": "No API keys configured",
            "text": "",
            "parsed": {},
        }

    gateway = KeyGateway(keys)
    session = build_session()

    try:
        # Submit
        print(f"[OCR] Submitting: {pdf_path}")
        job_id = submit_job(session, gateway, pdf_path)
        if not job_id:
            return {
                "success": False,
                "error": "Failed to submit OCR job",
                "text": "",
                "parsed": {},
            }

        # Poll
        print(f"[OCR] Polling job {job_id}...")
        completed = poll_job(session, gateway, job_id)
        if not completed:
            return {
                "success": False,
                "error": "OCR job failed or timed out",
                "text": "",
                "parsed": {},
            }

        # Extract + Parse
        text = extract_text(completed)
        parsed = parse_scan_markdown(text)

        return {"success": True, "text": text, "parsed": parsed, "error": ""}

    except Exception as e:
        return {"success": False, "error": str(e), "text": "", "parsed": {}}
    finally:
        session.close()

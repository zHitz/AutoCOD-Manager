"""
LDPlayer Manager — CLI wrapper for ldconsole.exe.
Provides full instance discovery, start/stop, and macro operations.
"""
import subprocess
import json
import os
from backend.config import config

# Resolve ldconsole.exe path from adb_path
# adb_path is like C:\LDPlayer\LDPlayer9\adb.exe
# ldconsole is at    C:\LDPlayer\LDPlayer9\ldconsole.exe
LDCONSOLE_PATH = os.path.join(
    os.path.dirname(config.adb_path), "ldconsole.exe"
)

OPERATIONS_DIR = os.path.join(
    os.path.dirname(config.adb_path), "vms", "operationRecords"
)


def _run(args: list, timeout: int = 15) -> str:
    """Execute ldconsole command and return stdout."""
    cmd = [LDCONSOLE_PATH] + args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8"
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return ""
    except FileNotFoundError:
        print(f"[LDPlayer] ldconsole not found at: {LDCONSOLE_PATH}")
        return ""


def list_all_instances() -> list[dict]:
    """List ALL LDPlayer instances (online + offline).

    Uses `ldconsole list2` which returns:
        index, name, top_win, bind_handle, running, pid_vbox, pid_player, w, h, dpi
    """
    output = _run(["list2"])
    if not output:
        return []

    instances = []
    for line in output.strip().splitlines():
        parts = line.split(",")
        if len(parts) < 10:
            continue
        try:
            idx = int(parts[0])
            name = parts[1]
            running = int(parts[4]) == 1
            pid = int(parts[5]) if parts[5] != "-1" else None
            w, h, dpi = int(parts[7]), int(parts[8]), int(parts[9])

            instances.append({
                "index": idx,
                "name": name,
                "running": running,
                "pid": pid,
                "resolution": f"{w}x{h}",
                "dpi": dpi,
            })
        except (ValueError, IndexError):
            continue

    return instances


def launch_instance(index: int) -> bool:
    """Start an emulator by index."""
    output = _run(["launch", "--index", str(index)], timeout=30)
    # ldconsole launch doesn't return useful output, but doesn't error
    return True


def quit_instance(index: int) -> bool:
    """Stop an emulator by index."""
    _run(["quit", "--index", str(index)], timeout=15)
    return True


def get_operations(index: int) -> list[dict]:
    """List available macro scripts for an instance.

    Uses `ldconsole operatelist --index N` which returns JSON array.
    """
    output = _run(["operatelist", "--index", str(index)])
    if not output:
        return []
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return []


def get_operation_info(index: int, filename: str) -> dict:
    """Get detailed info about a macro script.

    Uses `ldconsole operateinfo --index N --file <name>`.
    """
    output = _run(["operateinfo", "--index", str(index), "--file", filename])
    if not output:
        return {}
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {}


def list_record_files() -> list[dict]:
    """List all .record files from the operations directory."""
    if not os.path.isdir(OPERATIONS_DIR):
        return []

    records = []
    for fname in os.listdir(OPERATIONS_DIR):
        if fname.endswith(".record"):
            fpath = os.path.join(OPERATIONS_DIR, fname)
            stat = os.stat(fpath)
            records.append({
                "filename": fname,
                "name": fname.replace(".record", ""),
                "size_bytes": stat.st_size,
                "modified": stat.st_mtime,
            })

    return sorted(records, key=lambda r: r["modified"], reverse=True)


def load_record_content(filename: str) -> str:
    """Load the JSON content of a .record file."""
    fpath = os.path.join(OPERATIONS_DIR, filename)
    if not os.path.exists(fpath):
        return ""
    with open(fpath, "r", encoding="utf-8") as f:
        return f.read()


def run_operation(index: int, filename: str) -> dict:
    """Execute a macro script on a specific emulator.

    Reads the .record file, writes to a temp file, and uses shell redirect
    to pipe it as the --content argument (bypasses Windows CLI length limits).
    Also returns estimated duration from operateinfo.
    """
    fpath = os.path.join(OPERATIONS_DIR, filename)
    if not os.path.exists(fpath):
        return {"success": False, "error": f"Record file not found: {filename}"}

    # Read the record content
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()

    # Get duration info
    info = get_operation_info(index, filename)
    duration_ms = 0
    if info and "info" in info:
        duration_ms = info["info"].get("circleDuration", 0)

    # Use a temp file to pass large JSON to ldconsole
    import tempfile
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    try:
        tmp.write(content)
        tmp.close()

        # ldconsole operaterecord --index N --content "$(type tmpfile)"
        # Use shell=True with file content read inline
        cmd = (
            f'"{LDCONSOLE_PATH}" operaterecord '
            f'--index {index} '
            f'--content "{tmp.name}"'
        )

        # Actually, ldconsole expects inline JSON, not a file path.
        # For small files: pass directly. For large: use PowerShell substitution.
        if len(content) < 8000:
            # Direct pass — fits in CLI
            result = subprocess.run(
                [LDCONSOLE_PATH, "operaterecord",
                 "--index", str(index),
                 "--content", content],
                capture_output=True, text=True, timeout=15, encoding="utf-8",
            )
            output = result.stdout.strip()
        else:
            # Large file — use PowerShell to read and substitute
            ps_cmd = (
                f'$c = Get-Content -Raw -Path "{tmp.name}"; '
                f'& "{LDCONSOLE_PATH}" operaterecord '
                f'--index {index} --content $c'
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True, text=True, timeout=30, encoding="utf-8",
            )
            output = result.stdout.strip()
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    # Check for success
    success = False
    try:
        resp = json.loads(output)
        success = resp.get("code") == 0
    except (json.JSONDecodeError, ValueError):
        success = "code" not in output.lower()

    return {
        "success": success,
        "output": output,
        "duration_ms": duration_ms,
    }


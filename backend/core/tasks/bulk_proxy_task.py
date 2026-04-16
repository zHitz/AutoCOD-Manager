import asyncio
import os
import subprocess
import time
from datetime import datetime

from backend.config import config
from backend.storage.database import database
from backend.core.ldplayer_manager import launch_instance, quit_instance, list_all_instances

ADB_PATH = config.adb_path or r"C:\LDPlayer\LDPlayer9\adb.exe"
PACKAGE_NAME = "com.scheler.superproxy"
DOWNLOAD_DIR = "/sdcard/Download"
MAX_CONCURRENT = 6
START_DELAY_SECONDS = 5

async def workflow_super_proxy_auto_connect(serial: str, generated_config: str):
    """Executes the proxy injection workflow via ADB."""
    temp_filename = f"proxy_{serial}.txt"
    local_path = os.path.join(os.path.dirname(__file__), temp_filename)
    
    with open(local_path, "w", encoding="utf-8") as f:
        f.write(generated_config)
    
    def run_adb(args: list[str]) -> str:
        cmd = [ADB_PATH, "-s", serial] + args
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return res.stdout.strip()
        except:
            return ""

    try:
        run_adb(["push", local_path, f"{DOWNLOAD_DIR}/{temp_filename}"])
        
        run_adb(["shell", "am", "force-stop", PACKAGE_NAME])
        await asyncio.sleep(1)
        
        run_adb(["shell", "monkey", "-p", PACKAGE_NAME, "-c", "android.intent.category.LAUNCHER", "1"])
        await asyncio.sleep(6) # Increase sleep to let boot up
        
        # Stop running Proxy
        run_adb(["shell", "input", "tap", "480", "320"])
        await asyncio.sleep(1.5)
        
        # Back to Home
        run_adb(["shell", "input", "tap", "47", "78"])
        await asyncio.sleep(1.5)
        
        # Click Menu
        run_adb(["shell", "input", "tap", "924", "78"])
        await asyncio.sleep(1.5)
        
        # Click Import proxies
        run_adb(["shell", "input", "tap", "480", "492"])
        await asyncio.sleep(2)
        
        # Click Search
        run_adb(["shell", "input", "tap", "792", "72"])
        await asyncio.sleep(1.5)
        
        # Type filename
        # Remove suffix .txt for search robustness
        search_term = temp_filename.replace('.txt', '')
        run_adb(["shell", "input", "text", search_term])
        await asyncio.sleep(1)
        
        # Enter
        run_adb(["shell", "input", "keyevent", "66"])
        await asyncio.sleep(2)
        
        # Select first result
        run_adb(["shell", "input", "tap", "200", "250"])
        await asyncio.sleep(3)
        
        # Click imported Proxy
        run_adb(["shell", "input", "tap", "480", "177"])
        await asyncio.sleep(2)
        
        # Click Start proxy
        run_adb(["shell", "input", "tap", "480", "320"])
        await asyncio.sleep(2)
        
        # Home button
        run_adb(["shell", "input", "keyevent", "3"])
        await asyncio.sleep(1)
    finally:
        if os.path.exists(local_path):
            os.remove(local_path)

async def _worker(queue: asyncio.Queue):
    while True:
        task = await queue.get()
        if task is None:
            break
            
        emu_index = task['emulator_index']
        generated_config = task['generated_config']
        serial = f"emulator-{5554 + emu_index * 2}"
        
        print(f"[BulkProxy] Starting emulator {emu_index} -> {serial}")
        try:
            launch_instance(emu_index)
            # Give emulator time to boot (typically 15-25s)
            await asyncio.sleep(25)
            
            print(f"[BulkProxy] Executing proxy workflow on {serial}")
            await workflow_super_proxy_auto_connect(serial, generated_config)
            
            print(f"[BulkProxy] Completed proxy setup. Shutting down {serial}")
            quit_instance(emu_index)
        except Exception as e:
            print(f"[BulkProxy ERROR] on {serial}: {e}")
        finally:
            queue.task_done()


def start_bulk_deployment():
    """Starts the asyncio task for bulk proxy deployment."""
    # We must attach to the existing running event loop of FastAPI
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_run_bulk_deployment())
    except RuntimeError:
        # If not running inside an active loop (e.g. tests), start one
        asyncio.run(_run_bulk_deployment())

async def _run_bulk_deployment():
    print("[BulkProxy] Starting Background Bulk Deployment...")
    proxies = await database.get_all_proxies()
    
    # Flatten task assignments
    assignments = []
    for p in proxies:
         for emu_index in p.get('assigned_emulators', []):
             assignments.append({
                 "emulator_index": emu_index,
                 "generated_config": p['generated_config']
             })
             
    if not assignments:
        print("[BulkProxy] No proxies assigned to any emulators. Aborting.")
        return
        
    queue = asyncio.Queue()
    
    # Fill queue
    for t in assignments:
        queue.put_nowait(t)
        
    workers_count = min(MAX_CONCURRENT, queue.qsize())
    tasks = []
    
    print(f"[BulkProxy] Booting up {workers_count} parallel workers for {queue.qsize()} tasks.")
    for i in range(workers_count):
        task = asyncio.create_task(_worker(queue))
        tasks.append(task)
        # Stagger the initial start of workers by 5 seconds
        if i < workers_count - 1:
            await asyncio.sleep(START_DELAY_SECONDS)
            
    await queue.join()
    
    for i in range(workers_count):
        queue.put_nowait(None)
    await asyncio.gather(*tasks)
    
    print("[BulkProxy] All Bulk Deployments Finished.")
    

import urllib.request
import json
import socket
from urllib.error import URLError

endpoints = [
    "/api/workflow/functions",
    "/api/workflow/templates",
    "/api/workflow/recipes",
    "/api/devices",
    "/api/groups",
    "/api/accounts",
    "/api/workflow/activity-registry",
]

base_url = "http://127.0.0.1:8000"

print("--- TESTING WORKFLOW APP ENDPOINTS ---")
for ep in endpoints:
    url = base_url + ep
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            status_code = response.getcode()
            if isinstance(data, list):
                print(f"[OK] {ep}: List with {len(data)} items")
            elif isinstance(data, dict):
                print(
                    f"[OK] {ep}: Dict with keys {list(data.keys())} | Status: {data.get('status')}"
                )
            else:
                print(f"[OK] {ep}: {type(data)}")
    except urllib.error.HTTPError as e:
        print(f"[ERROR 4xx/5xx] {ep}: {e.code} - {e.reason}")
    except URLError as e:
        if isinstance(e.reason, socket.timeout):
            print(f"[TIMEOUT] {ep}: Connection timed out")
        else:
            print(f"[ERROR] {ep}: {e.reason}")
    except Exception as e:
        print(f"[ERROR] {ep}: {str(e)}")

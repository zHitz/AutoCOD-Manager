import sys
import os
import time

# Thêm đường dẫn gốc để import modules trong backend
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(root_dir)

from backend.core.full_scan import start_full_scan, get_scan_status

def ws_progress_callback(event, data):
    """Hàm callback giả lập WebSocket để in log ra terminal."""
    print(f"\n[WS Callback] Event: '{event}' | Data: {data}")

def main():
    # Index emulator mặc định là 1, có thể thay đổi bằng tham số dòng lệnh
    # Ví dụ: python test_full_scan.py 2
    emulator_index = 1
    if len(sys.argv) > 1:
        try:
            emulator_index = int(sys.argv[1])
        except ValueError:
            print("Tham số dòng lệnh phải là số (emulator_index).")
            return

    print(f"Starting full scan test for emulator {emulator_index}...")

    # Gọi start_full_scan
    result = start_full_scan(
        emulator_index=emulator_index,
        emulator_name=f"BotInstance{emulator_index}",
        ws_callback=ws_progress_callback
    )

    if not result.get("success"):
        print(f"FAILED Could not start scan: {result.get('error')}")
        return

    print(f"SUCCESS Scan activated successfully: {result}")
    
    # Vòng lặp chờ scan hoàn tất
    print("\nTracking progress...")
    while True:
        time.sleep(2)  # Check mỗi 2 giây
        
        statuses = get_scan_status()
        current_status = None
        
        for s in statuses:
            if s.get("emulator_index") == emulator_index:
                current_status = s
                break
                
        if not current_status:
            print("WARNING Scan process not found in system.")
            break
            
        status = current_status.get("status")
        step = current_status.get("step")
        
        if status == "completed":
            print(f"\nCOMPLETED FULL SCAN COMPLETED!")
            print(f"- Time: {current_status.get('elapsed_ms')}ms")
            print(f"- Game ID: {current_status.get('game_id')}")
            print(f"- OCR Parsed Data: {current_status.get('data')}")
            break
            
        elif status == "failed":
            print(f"\nFAILED FULL SCAN FAILED!")
            print(f"- Error Details: {current_status.get('error')}")
            break

if __name__ == "__main__":
    main()

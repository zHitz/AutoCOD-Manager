Bảng đối chiếu: Full Scan → Database
📌 Luồng dữ liệu tổng thể
full_scan.py → ocr_client.run_ocr() → parse_scan_markdown() → parsed_data
full_scan.py → database.save_scan_snapshot(parsed_data) → DB
1️⃣ OCR Parser output (

parse_scan_markdown
 trả về gì?)
Field	Key trong parsed_data	Kiểu	Cách parse
Lord Name	lord_name	

str
Dòng sau keyword "Lord"
Power	power	int	Dòng sau keyword "Power", parse 14,837,914 → int
Hall Level	hall_level	int	Regex 

(\d+)
 từ dòng sau "HALLOFORDER" / "hall"
Market Level	market_level	int	Regex 

(\d+)
 từ dòng sau "BAZAAR" / "market"
Pet Token	pet_token	int	Số cuối cùng trong toàn bộ text
Gold	resources.gold	int	Dòng thứ 2 sau keyword "Gold" (total value)
Wood	resources.wood	int	Dòng thứ 2 sau keyword "Wood" (total value)
Ore	resources.ore	int	Dòng thứ 2 sau keyword "Ore" (total value)
Mana	resources.mana	int	Dòng thứ 2 sau keyword "Mana" (total value)
2️⃣ 

save_scan_snapshot()
 ghi vào DB những gì?
Bảng 

emulators
 (upsert)
Column	Nguồn dữ liệu	Ghi?	Ghi chú

emu_index
Param emulator_index	✅	Từ 

full_scan.py
 argument
serial	Param serial	✅	Từ _get_adb_serial()
name	Param emulator_name	✅	Từ 

full_scan.py
 argument
resolution	—	❌ Không ghi	Dùng default 960x540

status
—	✅	Luôn set ONLINE khi upsert
last_seen_at	Auto	✅	datetime.now().isoformat()
Bảng scan_snapshots (INSERT)
Column	Nguồn từ parsed_data	Ghi?	Ghi chú

emulator_id
FK → emulators.id	✅	Từ 

upsert_emulator()
scan_type	Param, default 'full_scan'	✅	
lord_name	parsed_data["lord_name"]	✅	✅ Khớp parser
power	parsed_data["power"]	✅	✅ Khớp parser
hall_level	parsed_data["hall_level"]	✅	✅ Khớp parser
market_level	parsed_data["market_level"]	✅	✅ Khớp parser
pet_token	parsed_data["pet_token"]	✅	✅ Khớp parser

scan_status
Param "completed"	✅	
duration_ms	elapsed_ms tính từ time.time()	✅	
raw_ocr_text	ocr_result["text"] (toàn bộ raw text)	✅	
Bảng scan_resources (INSERT per resource)
resource_type	Nguồn từ parsed_data	bag_value	total_value	bag_raw	total_raw
gold	parsed_data["resources"]["gold"]	⚠️	⚠️	❌	❌
wood	parsed_data["resources"]["wood"]	⚠️	⚠️	❌	❌
ore	parsed_data["resources"]["ore"]	⚠️	⚠️	❌	❌
mana	parsed_data["resources"]["mana"]	⚠️	⚠️	❌	❌
3️⃣ Các vấn đề phát hiện
⚠️ Vấn đề 1: Resources lưu sai cấu trúc (bag_value & total_value đều = total)
Parser trả về resources dạng int đơn giản:

python
result["resources"] = {"gold": 589700000, "wood": ..., "ore": ..., "mana": ...}
Nhưng 

save_scan_snapshot()
 kỳ vọng dict với key bag/total:

python
res_data = resources.get(res_type, {})  # Nhận int, không phải dict
if isinstance(res_data, dict):      # → KHÔNG match
    bag = res_data.get("bag", 0)
elif isinstance(res_data, (int, float)):  # → MATCH nhánh này
    bag = int(res_data)              # bag = total value
    total = int(res_data)            # total = total value
Kết quả: bag_value và total_value đều bằng nhau = giá trị total từ OCR. Parser chỉ lấy 1 giá trị (dòng thứ 2 = total), bỏ qua dòng thứ 1 (current/bag). Nên cả bag_value lẫn total_value đều = total.

⚠️ Vấn đề 2: bag_raw và total_raw không bao giờ được ghi
Parser không trả về raw text cho từng resource. Nó chỉ parse thành int. Nên cả 2 column bag_raw và total_raw trong scan_resources luôn = "" (empty string).

⚠️ Vấn đề 3: Parser bỏ qua giá trị bag (current) của resources
Parser chủ ý skip dòng thứ 1 (current = bag) và chỉ lấy dòng thứ 2 (total):

python
# Lấy dòng i+2 (total), bỏ qua i+1 (current/bag)
result["resources"][res_name] = _parse_resource_value(lines[i + 2])
Nghĩa là bag value không hề được thu thập từ OCR.

✅ Vấn đề 4: Không có vấn đề — Tất cả fields chính đều được ghi đúng
lord_name, power, hall_level, market_level, pet_token, 4 resource types (gold/wood/ore/mana) — tất cả đều được parse và ghi vào DB đúng.

📊 Tóm tắt tổng quan
Hạng mục	Trạng thái
Emulator info → DB	✅ Khớp hoàn toàn
Profile (lord_name, power) → DB	✅ Khớp hoàn toàn
Building levels (hall, market) → DB	✅ Khớp hoàn toàn
Pet Token → DB	✅ Khớp hoàn toàn
Resources (gold/wood/ore/mana) → DB	⚠️ Chỉ lưu total value, bag luôn = total
Resource raw text → DB	❌ Không bao giờ được lưu
Scan metadata (duration, status, raw_ocr_text) → DB	✅ Khớp hoàn toàn
Kết luận: Full Scan ghi đúng và đầy đủ tất cả các field chính vào Database. Điểm yếu duy nhất là parser không phân biệt bag vs total cho resources (cả hai đều = total) và không lưu raw text của từng resource riêng lẻ.
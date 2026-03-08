Toàn bộ dữ liệu hiển thị trên Page Account đều được load từ Database thông qua API GET /api/accounts → database.get_all_accounts(). Cụ thể:

#	Field trên UI	Nguồn Database	Bảng gốc	✅ Khớp?
1	Account ID (account_id)	accounts.id	

accounts
✅
2	Emulator Name (emu_name)	emulators.name	

emulators
✅
3	Emu Index (

emu_index
)	emulators.emu_index	

emulators
✅
4	Emulator Status (emu_status)	emulators.status	

emulators
✅
5	Lord Name (lord_name)	scan_snapshots.lord_name	scan_snapshots (latest)	✅
6	Power (power)	scan_snapshots.power	scan_snapshots (latest)	✅
7	Hall Level (hall_level)	scan_snapshots.hall_level	scan_snapshots (latest)	✅
8	Market Level (market_level)	scan_snapshots.market_level	scan_snapshots (latest)	✅
9	Pet Token (pet_token)	scan_snapshots.pet_token	scan_snapshots (latest)	✅
10	Gold (gold)	scan_resources.bag_value (type=gold)	scan_resources	✅
11	Wood (wood)	scan_resources.bag_value (type=wood)	scan_resources	✅
12	Ore (ore)	scan_resources.bag_value (type=ore)	scan_resources	✅
13	Login Method (login_method)	accounts.login_method	

accounts
✅
14	Email (email)	accounts.email	

accounts
✅
15	Provider (provider)	accounts.provider	

accounts
✅
16	Alliance (alliance)	accounts.alliance	

accounts
✅
17	Note (note)	accounts.note	

accounts
✅
18	Last Scan Time (last_scan_at)	scan_snapshots.created_at	scan_snapshots	✅
19	Last Seen (last_seen_at)	emulators.last_seen_at	

emulators
✅
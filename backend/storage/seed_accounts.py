"""
Seed script to create 5 sample accounts in the SQLite database for the Accounts page UI development.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Also set CWD for config.yaml loading
os.chdir(PROJECT_ROOT)

from backend.config import config

if not config.is_loaded:
    config.load()

from backend.storage.database import database

# Mock data based on _mockData in accounts.js
MOCK_ACCOUNTS = [
    {
        "emu_index": 1,
        "serial": "emulator-5554",
        "name": "LDPlayer-01",
        "lord_name": "DragonSlayer",
        "pow": 12.5,
        "hallLvl": 25,
        "marketLvl": 24,
        "petToken": 450,
        "login_method": "Google",
        "email": "dragon@gmail.com",
        "provider": "Global",
        "alliance": "[KOR] Warriors",
        "note": "Main account",
        "status": "ONLINE",
        "gold": 1200,
        "wood": 5500,
        "ore": 2100,
    },
    {
        "emu_index": 2,
        "serial": "emulator-5556",
        "name": "LDPlayer-02",
        "lord_name": "FarmBot_01",
        "pow": 2.1,
        "hallLvl": 11,
        "marketLvl": 10,
        "petToken": 12,
        "login_method": "Facebook",
        "email": "farm01@yahoo.com",
        "provider": "Global",
        "alliance": "None",
        "note": "Farm wood fast",
        "status": "OFFLINE",
        "gold": 100,
        "wood": 12000,
        "ore": 500,
    },
    {
        "emu_index": 3,
        "serial": "emulator-5558",
        "name": "LDPlayer-03",
        "lord_name": "FarmBot_02",
        "pow": 1.8,
        "hallLvl": 9,
        "marketLvl": 9,
        "petToken": 5,
        "login_method": "Facebook",
        "email": "farm02@yahoo.com",
        "provider": "Global",
        "alliance": "None",
        "note": "Farm ore",
        "status": "ONLINE",
        "gold": 200,
        "wood": 1000,
        "ore": 15500,
    },
    {
        "emu_index": 4,
        "serial": "emulator-5560",
        "name": "LDPlayer-04",
        "lord_name": "SniperWolf",
        "pow": 8.4,
        "hallLvl": 22,
        "marketLvl": 20,
        "petToken": 120,
        "login_method": "Apple",
        "email": "-",
        "provider": "Global",
        "alliance": "[US] Eagles",
        "note": "Alt attack",
        "status": "OFFLINE",
        "gold": 4500,
        "wood": 2200,
        "ore": 3100,
    },
    {
        "emu_index": 5,
        "serial": "emulator-5562",
        "name": "LDPlayer-05",
        "lord_name": "Test",
        "pow": 3.5,
        "hallLvl": 15,
        "marketLvl": 15,
        "petToken": 60,
        "login_method": "Google",
        "email": "miner@gmail.com",
        "provider": "Funtap",
        "alliance": "[KOR] Warriors",
        "note": "Supply main",
        "status": "ONLINE",
        "gold": 25000,
        "wood": 18000,
        "ore": 22000,
    },
]


async def seed():
    print("Initialize DB sync...")
    database.init_sync()

    print("Seeding database with 5 mock accounts...")

    for acc in MOCK_ACCOUNTS:
        print(f"-> Processing emulator {acc['emu_index']} ({acc['name']})...")

        # 1. Provide Context for Emulator
        emu_id = await database.upsert_emulator(
            emu_index=acc["emu_index"],
            serial=acc["serial"],
            name=acc["name"],
            status=acc["status"],
        )
        print(f"   Created emulator (ID: {emu_id})")

        # 2. Add Scan Snapshot
        parsed_data = {
            "lord_name": acc["lord_name"],
            "power": int(acc["pow"] * 1000000),  # E.g. 12.5M -> 12500000
            "hall_level": acc["hallLvl"],
            "market_level": acc["marketLvl"],
            "pet_token": acc["petToken"],
            "resources": {
                "gold": {
                    "bag": int(acc["gold"] * 1000),
                    "total": int(acc["gold"] * 1000),
                },
                "wood": {
                    "bag": int(acc["wood"] * 1000),
                    "total": int(acc["wood"] * 1000),
                },
                "ore": {"bag": int(acc["ore"] * 1000), "total": int(acc["ore"] * 1000)},
            },
        }
        snap_id = await database.save_scan_snapshot(
            emulator_index=acc["emu_index"],
            serial=acc["serial"],
            emulator_name=acc["name"],
            parsed_data=parsed_data,
            scan_type="full_scan",
            scan_status="completed",
        )
        print(f"   Created scan snapshot (ID: {snap_id})")

        # 3. Add Account Record
        acc_id = await database.upsert_account(
            emulator_id=emu_id,
            login_method=acc["login_method"],
            email=acc["email"],
            provider=acc["provider"],
            alliance=acc["alliance"],
            note=acc["note"],
        )
        print(f"   Created user account (ID: {acc_id})")

    print("Done! Verify data by checking the API GET /api/accounts.")


if __name__ == "__main__":
    asyncio.run(seed())

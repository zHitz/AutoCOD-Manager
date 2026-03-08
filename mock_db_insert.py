import sqlite3
import os

db_path = r"f:\COD_CHECK\UI_MANAGER\data\cod_manager.db"


def insert_mock_data():
    if not os.path.exists(db_path):
        print(f"DB not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Insert a very complete mock record
    mock_data = (
        1,
        "emulator-5556",
        "BotInstance1",
        "MockLord_ProVIP",
        45900800,
        25,
        24,
        88500,
        15500000,
        8900000,
        4200000,
        1100000,
        "completed",
        45000,
        "MOCK OCR TEXT",
    )

    cursor.execute(
        """
        INSERT INTO emulator_data (
            emulator_index, serial, emulator_name,
            lord_name, power, hall_level, market_level, pet_token,
            gold, wood, ore, mana,
            scan_status, scan_duration_ms, raw_ocr_text
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        mock_data,
    )

    conn.commit()
    conn.close()
    print("Mock data successfully inserted into emulator_data table.")


if __name__ == "__main__":
    insert_mock_data()

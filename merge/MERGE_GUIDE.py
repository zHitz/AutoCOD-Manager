# -*- coding: utf-8 -*-
# WORKFLOW MERGE GUIDE
# Tai lieu hop nhat cac workflow moi vao nhanh main
# Ngay tao: 2026-03-13

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ============================================================================
# MỤC ĐÍCH:
# File này liệt kê TẤT CẢ dependencies (phụ thuộc) mà các workflow mới cần.
# Khi merge vào main, dev cần đảm bảo các thay đổi dưới đây có mặt đầy đủ.
# ============================================================================


# ============================
# 1. CÁC FILE WORKFLOW MỚI
# ============================
# Copy nguyên các file này vào thư mục workflow/:
WORKFLOW_FILES = [
    "workflow/tavern_chest_workflow.py",         # Tavern Chest Draw (Hero + Artifact)
    "workflow/troop_healing_workflow.py",         # Troop Healing
    "workflow/chat_with_hero.py",                 # Chat With Hero (standalone, tự xử lý template matching)
    "workflow/attack_darkling_legions_v1_basic.py", # Attack Darkling Legions V1
    "workflow/alliance_help_workflow.py",         # Alliance Help
]


# ============================
# 2. CÁC HÀM MỚI TRONG core_actions.py
# ============================
# Các hàm sau PHẢI có mặt trong core_actions.py trên main.
# Nếu main chưa có → copy hàm từ dev branch.
# Nếu main đã có phiên bản cũ → so sánh cẩn thận trước khi merge.

CORE_ACTIONS_REQUIRED_FUNCTIONS = {

    # --- Workflow: tavern_chest_workflow.py ---
    "claim_daily_chests": {
        "called_by": "tavern_chest_workflow.py",
        "description": "Claim daily free Hero & Artifact chest draws at Tavern",
        "depends_on_functions": [
            "go_to_construction",   # navigate to TAVERN building
            "wait_for_state",       # verify TAVERN screen reached
            "back_to_lobby",        # (inside go_to_construction)
        ],
        "depends_on_templates": [
            "TAVERN",               # construction_configs (state_detector.py)
            "TAVERN_FREE_DRAW",     # activity_configs (state_detector.py)
            "TAVERN_DRAW_X10",      # activity_configs (state_detector.py)
        ],
        "depends_on_construction_data": ["TAVERN"],
        "status": "Placeholder TODO coords — user chưa điền tọa độ thật",
    },

    # --- Workflow: troop_healing_workflow.py ---
    "heal_troops": {
        "called_by": "troop_healing_workflow.py",
        "description": "Heal wounded troops via Elixir or other methods",
        "depends_on_functions": [
            "go_to_construction",   # navigate to ELIXIR_HEALING
            "wait_for_state",
            "back_to_lobby",
        ],
        "depends_on_templates": [
            "ELIXIR_HEALING",       # construction_configs
            "HEALING_ICON",         # icon_configs
        ],
        "depends_on_construction_data": ["ELIXIR_HEALING"],
        "status": "Đã có tọa độ thật",
    },

    # --- Workflow: attack_darkling_legions_v1_basic.py ---
    "attack_darkling_legions_v1_basic": {
        "called_by": "attack_darkling_legions_v1_basic.py",
        "description": "Basic Darkling Legions attack — search menu → dispatch",
        "depends_on_functions": [
            "back_to_lobby",        # target OUT_CITY
            "wait_for_state",
        ],
        "depends_on_templates": [
            "AUTO_PEACEKEEPING",    # special_configs
        ],
        "depends_on_construction_data": [],
        "status": "Đã có tọa độ thật",
    },

    # --- Workflow: alliance_help_workflow.py ---
    "alliance_help": {
        "called_by": "alliance_help_workflow.py",
        "description": "Alliance Help — navigate to Alliance Menu, detect & tap Help button",
        "depends_on_functions": [
            "go_to_alliance",       # navigate to ALLIANCE_MENU
            "back_to_lobby",        # (inside go_to_alliance)
            "ensure_lobby_menu_open",
            "wait_for_state",
        ],
        "depends_on_templates": [
            "ALLIANCE_MENU",        # construction_configs
            "ALLIANCE_HELP",        # alliance_configs  ← MỚI
        ],
        "depends_on_construction_data": [],
        "extra_imports": ["import random"],  # core_actions.py cần import random
        "status": "Placeholder templates — user chưa chụp ảnh alliance_help_btn.png",
    },
}

# --- Workflow: chat_with_hero.py ---
# File này là STANDALONE (không gọi hàm riêng từ core_actions, tự xử lý template matching)
CHAT_WITH_HERO_DEPENDENCIES = {
    "called_by": "chat_with_hero.py (standalone file)",
    "description": "Chat with heroes on IN_CITY map — clockwise viewport scan",
    "core_actions_functions_used": [
        "startup_to_lobby",
        "back_to_lobby",
    ],
    "own_template_matching": True,  # Tự dùng cv2.matchTemplate, không dùng detector
    "depends_on_templates_files": [
        "templates/icon_markers/hero_chat_1.png",
        "templates/icon_markers/hero_chat_2.png",
        "templates/icon_markers/hero_chat_3.png",
    ],
    "depends_on_special_state": [
        "SKIP",  # special_configs (icon_markers/skip.png)
    ],
    "extra_imports": ["import cv2"],  # Workflow file cần OpenCV
    "status": "Đã hoạt động",
}


# ============================
# 3. CHUNG: CÁC HÀM CŨ BẮT BUỘC PHẢI CÓ
# ============================
# Các hàm dưới đây là nền tảng mà TẤT CẢ workflow mới đều dùng.
# Nếu main thiếu bất kỳ hàm nào → sẽ crash.

COMMON_REQUIRED_FUNCTIONS = [
    "ensure_app_running",       # Boot game nếu chưa chạy
    "startup_to_lobby",         # Boot game + navigate to lobby (ALL workflows dùng)
    "wait_for_state",           # Đợi game đạt target state
    "back_to_lobby",            # Navigate về lobby từ bất kỳ state nào
    "check_app_crash",          # Kiểm tra game crash/freeze
    "ensure_lobby_menu_open",   # Mở lobby expandable menu
    "go_to_construction",       # Navigate vào building bất kỳ
    "go_to_alliance",           # Navigate vào Alliance Menu
]


# ============================
# 4. THAY ĐỔI TRONG state_detector.py
# ============================
# Các entry sau PHẢI có mặt trong state_detector.py trên main.

STATE_DETECTOR_CHANGES = {

    "construction_configs": {
        # Entry mới (chưa có trên main cũ):
        "NEW_ENTRIES": {
            '"contructions/con_tavern.png": "TAVERN"': "REQUIRED by claim_daily_chests()",
        },
        # Entry cũ bắt buộc (verify không bị xóa):
        "MUST_EXIST": [
            '"contructions/con_hall.png": "HALL"',
            '"contructions/con_market.png": "MARKET"',
            '"contructions/con_elixir_healing.png": "ELIXIR_HEALING"',
            '"contructions/con_alliance_menu.png": "ALLIANCE_MENU"',
            '"contructions/con_research_center.png": "RESEARCH_CENTER"',
        ],
    },

    "activity_configs": {
        "NEW_ENTRIES": {
            '"tavern/free_draw_btn.png": "TAVERN_FREE_DRAW"': "REQUIRED by claim_daily_chests()",
            '"tavern/draw_x10_btn.png": "TAVERN_DRAW_X10"': "REQUIRED by claim_daily_chests()",
        },
    },

    "alliance_configs": {
        "NEW_ENTRIES": {
            '"alliance/alliance_help_btn.png": "ALLIANCE_HELP"': "REQUIRED by alliance_help()",
        },
        "MUST_EXIST": [
            '"alliance/war.png": "ALLIANCE_WAR"',
            '"alliance/no_rally.png": "NO_RALLY"',
            '"alliance/already_join_rally.png": "ALREADY_JOIN_RALLY"',
        ],
    },

    "special_configs": {
        "MUST_EXIST": [
            '"auto-peacekeeping.png": "AUTO_PEACEKEEPING"',
            '"icon_markers/skip.png": "SKIP"',
        ],
    },
}


# ============================
# 5. THAY ĐỔI TRONG construction_data.py
# ============================

CONSTRUCTION_DATA_CHANGES = {
    "NEW_ENTRIES": {
        "TAVERN": {
            "taps": [(0, 0), (0, 0)],  # TODO: User điền tọa độ thật
            "required_by": "claim_daily_chests() → go_to_construction('TAVERN')",
        },
    },
    "MUST_EXIST": [
        "HALL",
        "MARKET",
        "ELIXIR_HEALING",
        "SHOP",
        "RESEARCH_CENTER",
    ],
}


# ============================
# 6. TEMPLATE FILES (HÌNH ẢNH) CẦN CÓ
# ============================
# Copy các file ảnh vào thư mục templates/ tương ứng.
# Nếu thiếu → detector sẽ print WARNING nhưng không crash.

TEMPLATE_FILES = {
    # --- Đã có sẵn (verify không bị thiếu) ---
    "EXISTING": [
        "templates/contructions/con_tavern.png",
        "templates/contructions/con_alliance_menu.png",
        "templates/contructions/con_elixir_healing.png",
        "templates/contructions/con_research_center.png",
        "templates/alliance/war.png",
        "templates/alliance/no_rally.png",
        "templates/alliance/already_join_rally.png",
        "templates/auto-peacekeeping.png",
        "templates/icon_markers/skip.png",
        "templates/icon_markers/hero_chat_1.png",
        "templates/icon_markers/hero_chat_2.png",
        "templates/icon_markers/hero_chat_3.png",
        "templates/icon_markers/healing_icon.png",
    ],

    # --- CẦN CHỤP MỚI (user chưa tạo) ---
    "NEED_CAPTURE": [
        {
            "path": "templates/alliance/alliance_help_btn.png",
            "used_by": "alliance_help()",
            "description": "Nút Alliance Help trong Alliance Menu",
        },
        {
            "path": "templates/tavern/free_draw_btn.png",
            "used_by": "claim_daily_chests()",
            "description": "Nút Free Draw trên màn hình Hero Recruitment / Artifact",
        },
        {
            "path": "templates/tavern/draw_x10_btn.png",
            "used_by": "claim_daily_chests()",
            "description": "Nút x10 Draw (chỉ hiện khi có >= 10 keys)",
        },
    ],
}


# ============================
# 7. IMPORT MỚI TRONG core_actions.py
# ============================
# Dòng import sau cần có ở đầu file core_actions.py:

NEW_IMPORTS_IN_CORE_ACTIONS = [
    "import random",  # Dùng bởi alliance_help() cho random interval
]
# Các import khác (os, sys, time, cv2, numpy, adb_helper, v.v.) đã có sẵn.


# ============================
# 8. CHECKLIST MERGE
# ============================

MERGE_CHECKLIST = """
+==============================================================+
|                    MERGE CHECKLIST                            |
+==============================================================+
|                                                              |
|  [ ] 1. core_actions.py                                      |
|     [ ] Them `import random` o dau file                      |
|     [ ] Them ham: alliance_help()                            |
|     [ ] Them ham: claim_daily_chests()                       |
|     [ ] Verify ham: heal_troops() da co                      |
|     [ ] Verify ham: attack_darkling_legions_v1_basic() da co |
|     [ ] Verify ham: go_to_alliance() da co                   |
|     [ ] Verify ham: go_to_construction() da co               |
|                                                              |
|  [ ] 2. state_detector.py                                    |
|     [ ] construction_configs: them con_tavern.png -> TAVERN  |
|     [ ] activity_configs: them tavern/free_draw_btn.png      |
|     [ ] activity_configs: them tavern/draw_x10_btn.png       |
|     [ ] alliance_configs: them alliance_help_btn.png         |
|                                                              |
|  [ ] 3. construction_data.py                                 |
|     [ ] Them TAVERN entry (placeholder coords)               |
|                                                              |
|  [ ] 4. Template files                                       |
|     [ ] Tao thu muc: templates/tavern/                       |
|     [ ] Verify: templates/alliance/ co du 3 file cu          |
|     [ ] Verify: templates/icon_markers/ co hero_chat_*.png   |
|                                                              |
|  [ ] 5. Workflow files                                       |
|     [ ] Copy: tavern_chest_workflow.py                       |
|     [ ] Copy: troop_healing_workflow.py                      |
|     [ ] Copy: chat_with_hero.py                              |
|     [ ] Copy: attack_darkling_legions_v1_basic.py            |
|     [ ] Copy: alliance_help_workflow.py                      |
|                                                              |
+==============================================================+
"""

if __name__ == "__main__":
    print(MERGE_CHECKLIST)
    print("\n=== WORKFLOW FILES ===")
    for f in WORKFLOW_FILES:
        print(f"  -> {f}")

    print("\n=== NEW CORE ACTIONS FUNCTIONS ===")
    for name, info in CORE_ACTIONS_REQUIRED_FUNCTIONS.items():
        print(f"  -> {name}() | Called by: {info['called_by']} | Status: {info['status']}")

    print("\n=== TEMPLATE FILES NEED CAPTURE ===")
    for t in TEMPLATE_FILES["NEED_CAPTURE"]:
        print(f"  -> {t['path']} | {t['description']}")

    print("\n=== NEW IMPORTS IN core_actions.py ===")
    for imp in NEW_IMPORTS_IN_CORE_ACTIONS:
        print(f"  -> {imp}")

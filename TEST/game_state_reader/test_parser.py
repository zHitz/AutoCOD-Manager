"""Tests for PET SANCTUARY hierarchy parsing."""

from __future__ import annotations

from pathlib import Path
import sys


CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from parser import (
    ERROR_PET_SANCTUARY_NOT_CONFIRMED,
    ERROR_PET_TOKEN_NOT_FOUND,
    ERROR_UNSUPPORTED_RENDER_SURFACE,
    parse_hierarchy_xml,
)


def _wrap_nodes(*nodes: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<hierarchy rotation="0">'
        + "".join(nodes)
        + "</hierarchy>"
    )


def test_parse_success_with_neighbor_token_value():
    xml_text = _wrap_nodes(
        '<node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.game" bounds="[0,0][960,540]">',
        '<node index="0" text="PET SANCTUARY" resource-id="screen_title" class="android.widget.TextView" package="com.game" bounds="[30,10][300,60]" />',
        '<node index="1" text="Pet Token" resource-id="pet_token_label" class="android.widget.TextView" package="com.game" bounds="[640,10][780,60]" />',
        '<node index="2" text="12,345" resource-id="pet_token_value" class="android.widget.TextView" package="com.game" bounds="[790,10][930,60]" />',
        "</node>",
    )

    result = parse_hierarchy_xml(xml_text)

    assert result["ok"] is True
    assert result["screen"] == "PET_SANCTUARY"
    assert result["pet_token"] == 12345
    assert result["error"] is None


def test_parse_fails_when_screen_not_confirmed():
    xml_text = _wrap_nodes(
        '<node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.game" bounds="[0,0][960,540]">',
        '<node index="0" text="PET ENCLOSURE" resource-id="screen_title" class="android.widget.TextView" package="com.game" bounds="[30,10][300,60]" />',
        '<node index="1" text="Pet Token" resource-id="pet_token_label" class="android.widget.TextView" package="com.game" bounds="[640,10][780,60]" />',
        '<node index="2" text="12,345" resource-id="pet_token_value" class="android.widget.TextView" package="com.game" bounds="[790,10][930,60]" />',
        "</node>",
    )

    result = parse_hierarchy_xml(xml_text)

    assert result["ok"] is False
    assert result["screen"] is None
    assert result["pet_token"] is None
    assert result["error"] == ERROR_PET_SANCTUARY_NOT_CONFIRMED


def test_parse_fails_when_token_missing():
    xml_text = _wrap_nodes(
        '<node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.game" bounds="[0,0][960,540]">',
        '<node index="0" text="PET SANCTUARY" resource-id="screen_title" class="android.widget.TextView" package="com.game" bounds="[30,10][300,60]" />',
        '<node index="1" text="Daily Reward" resource-id="reward_label" class="android.widget.TextView" package="com.game" bounds="[640,10][780,60]" />',
        '<node index="2" text="Claim" resource-id="claim_button" class="android.widget.Button" package="com.game" bounds="[790,10][930,60]" />',
        "</node>",
    )

    result = parse_hierarchy_xml(xml_text)

    assert result["ok"] is False
    assert result["screen"] == "PET_SANCTUARY"
    assert result["pet_token"] is None
    assert result["error"] == ERROR_PET_TOKEN_NOT_FOUND


def test_parse_fails_for_empty_render_surface():
    xml_text = _wrap_nodes(
        '<node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="" bounds="[0,0][960,540]" />'
    )

    result = parse_hierarchy_xml(xml_text)

    assert result["ok"] is False
    assert result["error"] == ERROR_UNSUPPORTED_RENDER_SURFACE


def test_parse_fails_for_unity_surface_only_dump():
    xml_text = _wrap_nodes(
        '<node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.game" bounds="[0,0][960,540]">',
        '<node index="0" text="" resource-id="com.game:id/action_bar_root" class="android.widget.LinearLayout" package="com.game" bounds="[0,0][960,540]" />',
        '<node index="1" text="" resource-id="android:id/content" class="android.widget.FrameLayout" package="com.game" bounds="[0,0][960,540]" />',
        '<node index="2" text="" resource-id="com.game:id/unitySurfaceView" content-desc="Game view" class="android.view.View" package="com.game" bounds="[0,0][960,540]" />',
        "</node>",
    )

    result = parse_hierarchy_xml(xml_text)

    assert result["ok"] is False
    assert result["screen"] is None
    assert result["pet_token"] is None
    assert result["error"] == ERROR_UNSUPPORTED_RENDER_SURFACE

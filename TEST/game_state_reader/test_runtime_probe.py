"""Tests for runtime log probing helpers."""

from __future__ import annotations

from pathlib import Path
import sys


CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from runtime_probe import (
    _extract_json_responses,
    _extract_printable_strings,
    _extract_role_id,
    _find_pet_token_candidates,
    _find_role_file_pet_token_candidates,
    _parse_doc_listing,
)


def test_extract_role_id_from_park_log_line():
    text = "I/CustomerService: setCustomerServiceUserInfo appUid:1800981 roleId:22505969"
    assert _extract_role_id(text) == 22505969


def test_extract_json_response_and_pet_token_candidate():
    text = (
        "2026-03-30 14:22:42.203 D/JsonResponse: parseData v2 = /v1/pet/sanctuary/info, "
        'response = {"result":{"code":0},"data":{"petToken":426,"name":"Sanctuary"}}'
    )

    responses = _extract_json_responses(text)
    candidates = _find_pet_token_candidates(responses)

    assert responses[0]["endpoint"] == "/v1/pet/sanctuary/info"
    assert candidates == [
        {
            "endpoint": "/v1/pet/sanctuary/info",
            "path": "data.petToken",
            "value": 426,
            "source": "json_response",
        }
    ]


def test_extract_printable_strings_from_binary_payload():
    payload = b"\xff\x04token_name\x00PET_SANCTUARY\x00petToken\x00426\x00"
    strings = _extract_printable_strings(payload)

    assert "token_name" in strings
    assert "PET_SANCTUARY" in strings
    assert "petToken" in strings


def test_find_pet_token_candidate_from_role_file_strings():
    candidates = _find_role_file_pet_token_candidates(
        [
            {
                "name": "QuestSave22505969",
                "printable_strings": ["lastReward", "petToken", "426", "otherField"],
            }
        ]
    )

    assert candidates == [
        {
            "file": "QuestSave22505969",
            "path": "QuestSave22505969[2]",
            "value": 426,
            "source": "role_file_printable_strings",
        }
    ]


def test_parse_doc_listing_line():
    doc_listing = (
        "-rw-rw---- 1 u0_a60 sdcard_rw 125 2026-03-30 14:17 QuestSave22505969\n"
        "-rw-rw---- 1 u0_a60 sdcard_rw 39 2026-03-30 14:22 Mark_22505969\n"
    )

    entries = _parse_doc_listing(doc_listing)

    assert entries == [
        {"name": "QuestSave22505969", "size": 125},
        {"name": "Mark_22505969", "size": 39},
    ]

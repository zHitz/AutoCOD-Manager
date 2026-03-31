"""Parse Android UI hierarchy dumps for PET SANCTUARY research."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


ERROR_NAV_TARGET_NOT_REACHED = "NAV_TARGET_NOT_REACHED"
ERROR_HIERARCHY_DUMP_FAILED = "HIERARCHY_DUMP_FAILED"
ERROR_PET_SANCTUARY_NOT_CONFIRMED = "PET_SANCTUARY_NOT_CONFIRMED"
ERROR_PET_TOKEN_NOT_FOUND = "PET_TOKEN_NOT_FOUND"
ERROR_UNSUPPORTED_RENDER_SURFACE = "UNSUPPORTED_RENDER_SURFACE"

_BOUNDS_RE = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")
_DIGIT_RE = re.compile(r"\d[\d, ]*")


@dataclass(slots=True)
class NodeRecord:
    """Flattened node data extracted from the hierarchy dump."""

    node_id: str
    parent_id: str | None
    index: int
    text: str
    content_desc: str
    resource_id: str
    class_name: str
    package: str
    bounds: tuple[int, int, int, int] | None

    def fields(self) -> list[str]:
        return [self.text, self.content_desc, self.resource_id]


def _normalize(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "", str(value or "").upper())


def _parse_bounds(value: str) -> tuple[int, int, int, int] | None:
    match = _BOUNDS_RE.fullmatch(str(value or "").strip())
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def _extract_numbers(value: str) -> list[int]:
    numbers: list[int] = []
    for match in _DIGIT_RE.findall(str(value or "")):
        compact = match.replace(",", "").replace(" ", "")
        if compact.isdigit():
            numbers.append(int(compact))
    return numbers


def _is_meaningful(node: NodeRecord) -> bool:
    return any(field.strip() for field in node.fields())


def _contains_phrase(node: NodeRecord, phrase: str) -> bool:
    target = _normalize(phrase)
    return any(target in _normalize(field) for field in node.fields())


def _is_token_anchor(node: NodeRecord) -> bool:
    normalized_fields = [_normalize(field) for field in node.fields()]
    return any("PETTOKEN" in field for field in normalized_fields) or any(
        "PET" in field and "TOKEN" in field for field in normalized_fields
    )


def _node_center(bounds: tuple[int, int, int, int] | None) -> tuple[float, float]:
    if not bounds:
        return 0.0, 0.0
    x1, y1, x2, y2 = bounds
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def _distance(left: NodeRecord, right: NodeRecord) -> float:
    lx, ly = _node_center(left.bounds)
    rx, ry = _node_center(right.bounds)
    return abs(lx - rx) + abs(ly - ry)


def _y_overlap(left: NodeRecord, right: NodeRecord) -> bool:
    if not left.bounds or not right.bounds:
        return False
    _, ly1, _, ly2 = left.bounds
    _, ry1, _, ry2 = right.bounds
    return min(ly2, ry2) - max(ly1, ry1) >= 0


def _is_numeric_candidate(anchor: NodeRecord, node: NodeRecord) -> bool:
    if node.node_id == anchor.node_id:
        return False
    if not any(_extract_numbers(field) for field in node.fields()):
        return False
    if _is_token_anchor(node):
        return False
    return True


def _relation_rank(anchor: NodeRecord, candidate: NodeRecord) -> tuple[int, float]:
    if candidate.parent_id and candidate.parent_id == anchor.parent_id:
        return 0, _distance(anchor, candidate)
    if candidate.parent_id == anchor.node_id or anchor.parent_id == candidate.node_id:
        return 1, _distance(anchor, candidate)

    if anchor.bounds and candidate.bounds:
        ax1, _, ax2, _ = anchor.bounds
        cx1, _, _, _ = candidate.bounds
        if _y_overlap(anchor, candidate) and cx1 >= ax1:
            return 2, _distance(anchor, candidate)
        if _distance(anchor, candidate) <= 240:
            return 3, _distance(anchor, candidate)

        if cx1 > ax2 and _distance(anchor, candidate) <= 320:
            return 4, _distance(anchor, candidate)

    return 9, _distance(anchor, candidate)


def _flatten_nodes(root: ET.Element) -> list[NodeRecord]:
    nodes: list[NodeRecord] = []

    def walk(element: ET.Element, parent_id: str | None, counter: list[int]):
        node_id = f"node-{counter[0]}"
        counter[0] += 1
        node = NodeRecord(
            node_id=node_id,
            parent_id=parent_id,
            index=int(element.attrib.get("index", "0") or 0),
            text=element.attrib.get("text", "") or "",
            content_desc=element.attrib.get("content-desc", "") or "",
            resource_id=element.attrib.get("resource-id", "") or "",
            class_name=element.attrib.get("class", "") or "",
            package=element.attrib.get("package", "") or "",
            bounds=_parse_bounds(element.attrib.get("bounds", "")),
        )
        nodes.append(node)
        for child in list(element):
            walk(child, node_id, counter)

    walk(root, None, [0])
    return nodes


def _build_diagnostics(nodes: list[NodeRecord]) -> dict:
    meaningful = [node for node in nodes if _is_meaningful(node)]
    return {
        "node_count": len(nodes),
        "meaningful_node_count": len(meaningful),
        "sample_nodes": [
            {
                "text": node.text,
                "content_desc": node.content_desc,
                "resource_id": node.resource_id,
                "bounds": node.bounds,
            }
            for node in meaningful[:8]
        ],
    }


def _is_unity_surface_only(nodes: list[NodeRecord], diagnostics: dict) -> bool:
    meaningful = [node for node in nodes if _is_meaningful(node)]
    if not meaningful:
        return True

    unity_nodes = [
        node
        for node in meaningful
        if "UNITYSURFACEVIEW" in _normalize(node.resource_id) or _normalize(node.content_desc) == "GAMEVIEW"
    ]
    non_surface_nodes = [
        node
        for node in meaningful
        if node not in unity_nodes
        and _normalize(node.resource_id) not in {"COMFARLIGHTGAMESSAMOGPVNIDACTIONBARROOT", "ANDROIDIDCONTENT"}
    ]

    diagnostics["surface_analysis"] = {
        "unity_surface_count": len(unity_nodes),
        "non_surface_meaningful_count": len(non_surface_nodes),
        "unity_only": bool(unity_nodes) and not non_surface_nodes,
    }
    return bool(unity_nodes) and not non_surface_nodes


def _detect_screen(nodes: list[NodeRecord]) -> tuple[bool, list[dict]]:
    matches: list[dict] = []
    for node in nodes:
        if _contains_phrase(node, "PET SANCTUARY"):
            matches.append(
                {
                    "node_id": node.node_id,
                    "text": node.text,
                    "content_desc": node.content_desc,
                    "resource_id": node.resource_id,
                    "bounds": node.bounds,
                }
            )
    return bool(matches), matches


def _find_pet_token(nodes: list[NodeRecord]) -> tuple[int | None, dict]:
    anchors = [node for node in nodes if _is_token_anchor(node)]
    diagnostics = {
        "anchor_count": len(anchors),
        "anchors": [
            {
                "node_id": node.node_id,
                "text": node.text,
                "content_desc": node.content_desc,
                "resource_id": node.resource_id,
                "bounds": node.bounds,
            }
            for node in anchors[:6]
        ],
    }
    if not anchors:
        return None, diagnostics

    for anchor in anchors:
        same_node_numbers = []
        for field in anchor.fields():
            same_node_numbers.extend(_extract_numbers(field))
        unique_numbers = sorted(set(same_node_numbers))
        if len(unique_numbers) == 1:
            diagnostics["selected_from"] = "same_node"
            diagnostics["selected_anchor"] = anchor.node_id
            return unique_numbers[0], diagnostics

    ranked_candidates: list[tuple[tuple[int, float], NodeRecord, NodeRecord, int]] = []
    for anchor in anchors:
        for candidate in nodes:
            if not _is_numeric_candidate(anchor, candidate):
                continue
            numbers = []
            for field in candidate.fields():
                numbers.extend(_extract_numbers(field))
            if len(numbers) != 1:
                continue
            rank = _relation_rank(anchor, candidate)
            if rank[0] > 4:
                continue
            ranked_candidates.append((rank, anchor, candidate, numbers[0]))

    if not ranked_candidates:
        return None, diagnostics

    ranked_candidates.sort(key=lambda item: item[0])
    best_rank, best_anchor, best_candidate, best_value = ranked_candidates[0]
    diagnostics["selected_from"] = "neighbor_node"
    diagnostics["selected_anchor"] = best_anchor.node_id
    diagnostics["selected_candidate"] = {
        "node_id": best_candidate.node_id,
        "text": best_candidate.text,
        "content_desc": best_candidate.content_desc,
        "resource_id": best_candidate.resource_id,
        "bounds": best_candidate.bounds,
        "relation_rank": best_rank[0],
        "distance": best_rank[1],
    }
    return best_value, diagnostics


def parse_hierarchy_xml(xml_text: str) -> dict:
    """Parse raw hierarchy XML into a normalized PET SANCTUARY result."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        return {
            "ok": False,
            "screen": None,
            "pet_token": None,
            "error": ERROR_HIERARCHY_DUMP_FAILED,
            "diagnostics": {"parse_error": str(exc)},
        }

    nodes = _flatten_nodes(root)
    diagnostics = _build_diagnostics(nodes)

    if diagnostics["node_count"] < 2 or diagnostics["meaningful_node_count"] == 0:
        return {
            "ok": False,
            "screen": None,
            "pet_token": None,
            "error": ERROR_UNSUPPORTED_RENDER_SURFACE,
            "diagnostics": diagnostics,
        }

    if _is_unity_surface_only(nodes, diagnostics):
        return {
            "ok": False,
            "screen": None,
            "pet_token": None,
            "error": ERROR_UNSUPPORTED_RENDER_SURFACE,
            "diagnostics": diagnostics,
        }

    screen_confirmed, screen_matches = _detect_screen(nodes)
    diagnostics["screen_matches"] = screen_matches

    if not screen_confirmed:
        return {
            "ok": False,
            "screen": None,
            "pet_token": None,
            "error": ERROR_PET_SANCTUARY_NOT_CONFIRMED,
            "diagnostics": diagnostics,
        }

    pet_token, token_diagnostics = _find_pet_token(nodes)
    diagnostics["token_search"] = token_diagnostics

    if pet_token is None:
        return {
            "ok": False,
            "screen": "PET_SANCTUARY",
            "pet_token": None,
            "error": ERROR_PET_TOKEN_NOT_FOUND,
            "diagnostics": diagnostics,
        }

    return {
        "ok": True,
        "screen": "PET_SANCTUARY",
        "pet_token": pet_token,
        "error": None,
        "diagnostics": diagnostics,
    }


def parse_hierarchy_file(path: str | Path) -> dict:
    """Read and parse a hierarchy XML file from disk."""
    xml_path = Path(path)
    xml_text = xml_path.read_text(encoding="utf-8", errors="replace")
    result = parse_hierarchy_xml(xml_text)
    result["source_path"] = str(xml_path.resolve())
    return result

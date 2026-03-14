# Construction data: maps construction names to their tap sequences.
# Each entry is a list of (x, y) coordinates to tap in order.
# The construction name must match the key in state_detector's construction_configs.

CONSTRUCTION_TAPS = {
    "HALL": [
        (456, 111),
        (380, 116),
    ],
    "MARKET": [
        (639, 232),
        (545, 267),
    ],
    "ELIXIR_HEALING": [
        (705, 380),
        (793, 405),
    ],
    "SHOP": [
        (702, 279),
        (693, 351),
    ],
    "RESEARCH_CENTER": [
        # TODO: USER cần cung cấp tọa độ navigate từ IN_CITY
        (0, 0),
        (0, 0),
    ],
    "TAVERN": [
        # TODO: USER cần cung cấp tọa độ navigate từ IN_CITY
        (0, 0),
        (0, 0),
    ],
}

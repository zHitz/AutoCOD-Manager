"""
Data Validator — Sanity checks for OCR output.
Ensures data reliability per LOGIC_BUSSINESS.txt Section 5.
"""


class ValidationResult:
    """Result of a validation check."""

    def __init__(self, is_valid: bool, is_reliable: bool = True, errors: list = None):
        self.is_valid = is_valid
        self.is_reliable = is_reliable
        self.errors = errors or []

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "is_reliable": self.is_reliable,
            "errors": self.errors,
        }


class ErrorType:
    OCR_FAIL = "OCR_FAIL"
    NAVIGATION_FAIL = "NAVIGATION_FAIL"
    TIMEOUT = "TIMEOUT"
    VALIDATION_FAIL = "VALIDATION_FAIL"
    ADB_ERROR = "ADB_ERROR"


def validate_profile(data: dict) -> ValidationResult:
    """Validate profile scan result.

    Checks:
    - Name is non-empty and has > 2 chars
    - Power > 0
    """
    errors = []

    name = data.get("name", "")
    power = data.get("power", 0)

    if not name or len(name) < 2:
        errors.append("Name too short or empty")

    if not isinstance(power, (int, float)) or power <= 0:
        errors.append("Power must be positive")

    is_valid = len(errors) == 0
    # Mark as unreliable if name is suspiciously short
    is_reliable = is_valid and len(name) >= 3
    return ValidationResult(is_valid, is_reliable, errors)


def validate_resources(data: dict) -> ValidationResult:
    """Validate resource scan result.

    Checks:
    - total >= bag for each resource
    - No negative values
    - At least one resource > 0
    """
    errors = []
    any_positive = False

    for res_type in ["gold", "wood", "ore", "mana"]:
        entry = data.get(res_type, {})
        bag = entry.get("bag", 0)
        total = entry.get("total", 0)

        if bag < 0:
            errors.append(f"{res_type}.bag is negative ({bag})")
        if total < 0:
            errors.append(f"{res_type}.total is negative ({total})")
        if total < bag:
            errors.append(f"{res_type}.total ({total}) < bag ({bag})")
        if total > 0 or bag > 0:
            any_positive = True

    if not any_positive:
        errors.append("All resources are zero — possible OCR failure")

    is_valid = len(errors) == 0
    is_reliable = is_valid and any_positive
    return ValidationResult(is_valid, is_reliable, errors)


def validate_building_level(level: int) -> ValidationResult:
    """Validate building level."""
    errors = []
    if not isinstance(level, int) or level < 0:
        errors.append("Building level must be non-negative integer")
    if level > 50:
        errors.append(f"Building level suspiciously high ({level})")

    is_valid = len(errors) == 0
    return ValidationResult(is_valid, is_valid, errors)


def validate_pet_token(token: int) -> ValidationResult:
    """Validate pet token count."""
    errors = []
    if not isinstance(token, int) or token < 0:
        errors.append("Pet token must be non-negative integer")
    if token > 99999:
        errors.append(f"Pet token suspiciously high ({token})")

    is_valid = len(errors) == 0
    return ValidationResult(is_valid, is_valid, errors)

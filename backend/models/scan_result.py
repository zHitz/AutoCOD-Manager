"""
Data Models — Pydantic models for scan results and task execution.
Normalized data structures per LOGIC_BUSSINESS.txt Section 4.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────

class TaskType(str, Enum):
    PROFILE = "profile"
    RESOURCES = "resources"
    BUILDING = "building"
    PET = "pet"
    HALL = "hall"
    MARKET = "market"
    FULL_SCAN = "full_scan"


class TaskStatus(str, Enum):
    QUEUED = "QUEUED"
    NAVIGATING = "NAVIGATING"
    CAPTURING = "CAPTURING"
    PROCESSING = "PROCESSING"
    VALIDATING = "VALIDATING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"


# ──────────────────────────────────────────────
# Scan Data Models
# ──────────────────────────────────────────────

class ProfileData(BaseModel):
    name: str = ""
    power: int = 0
    power_raw: str = ""
    is_reliable: bool = True


class ResourceEntry(BaseModel):
    bag: int = 0
    total: int = 0
    bag_raw: str = ""
    total_raw: str = ""


class ResourceData(BaseModel):
    gold: ResourceEntry = Field(default_factory=ResourceEntry)
    wood: ResourceEntry = Field(default_factory=ResourceEntry)
    ore: ResourceEntry = Field(default_factory=ResourceEntry)
    mana: ResourceEntry = Field(default_factory=ResourceEntry)


class ScanReport(BaseModel):
    """Complete scan report for a single device."""
    serial: str
    timestamp: datetime = Field(default_factory=datetime.now)
    profile: Optional[ProfileData] = None
    resources: Optional[ResourceData] = None
    hall_level: Optional[int] = None
    market_level: Optional[int] = None
    pet_token: Optional[int] = None
    is_reliable: bool = True
    errors: list[str] = Field(default_factory=list)


# ──────────────────────────────────────────────
# Task Execution Models
# ──────────────────────────────────────────────

class TaskRequest(BaseModel):
    """API request to run a task."""
    serial: str
    task_type: TaskType


class TaskResult(BaseModel):
    """Result of a single task execution."""
    task_id: str
    task_type: TaskType
    serial: str
    status: TaskStatus
    data: Optional[dict] = None
    error: Optional[str] = None
    validation_errors: list[str] = Field(default_factory=list)
    is_reliable: bool = True
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_ms: int = 0

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class TaskQueueItem(BaseModel):
    """Item in the task queue."""
    task_id: str
    task_type: TaskType
    serial: str
    status: TaskStatus = TaskStatus.QUEUED
    progress_step: str = ""
    created_at: datetime = Field(default_factory=datetime.now)


# ──────────────────────────────────────────────
# API Response Models
# ──────────────────────────────────────────────

class DeviceInfo(BaseModel):
    serial: str
    status: str
    current_task: Optional[str] = None
    error_msg: str = ""


class HealthSummary(BaseModel):
    total: int = 0
    online: int = 0
    busy: int = 0
    offline: int = 0
    error: int = 0

"""
Task Queue — Async task execution with emulator locking.
Core requirement from LOGIC_BUSSINESS.txt Section 8.
"""
import asyncio
import uuid
import time
import threading
from datetime import datetime
from typing import Callable

from backend.core.emulator import emulator_manager, EmulatorStatus
from backend.core.ocr_engine import ocr_engine
from backend.core.navigator import navigator
from backend.core import validator
from backend.models.scan_result import (
    TaskStatus, TaskType, TaskResult, TaskQueueItem,
)


class TaskQueue:
    """Manages task execution with emulator locking and progress tracking."""

    def __init__(self):
        self._queue: list[TaskQueueItem] = []
        self._history: list[TaskResult] = []
        self._max_history = 200
        self._ws_callback: Callable | None = None
        self._lock = threading.Lock()

    def set_ws_callback(self, callback: Callable):
        """Set callback for WebSocket progress updates."""
        self._ws_callback = callback

    def _emit(self, event: str, data: dict):
        """Emit event via WebSocket callback."""
        if self._ws_callback:
            try:
                self._ws_callback(event, data)
            except Exception:
                pass

    def get_queue(self) -> list[dict]:
        """Get current queue state."""
        return [item.model_dump() for item in self._queue]

    def get_history(self, limit: int = 50) -> list[dict]:
        """Get task execution history."""
        return [r.model_dump() for r in self._history[-limit:]]

    def submit_task(self, serial: str, task_type: TaskType) -> str:
        """Submit a task for execution. Returns task_id."""
        task_id = str(uuid.uuid4())[:8]
        item = TaskQueueItem(
            task_id=task_id,
            task_type=task_type,
            serial=serial,
        )
        with self._lock:
            self._queue.append(item)

        self._emit("task_queued", {"task_id": task_id, "serial": serial, "type": task_type.value})

        # Execute in background thread
        thread = threading.Thread(
            target=self._execute_task, args=(item,), daemon=True
        )
        thread.start()
        return task_id

    def _execute_task(self, item: TaskQueueItem):
        """Execute a single task (runs in background thread)."""
        result = TaskResult(
            task_id=item.task_id,
            task_type=item.task_type,
            serial=item.serial,
            status=TaskStatus.QUEUED,
            started_at=datetime.now(),
        )

        emu = emulator_manager.get(item.serial)

        try:
            # Step 1: Acquire emulator lock
            item.status = TaskStatus.NAVIGATING
            self._emit("task_started", {
                "task_id": item.task_id, "serial": item.serial,
                "step": "Acquiring lock..."
            })

            if not emu.acquire(task_name=item.task_type.value):
                result.status = TaskStatus.FAILED
                result.error = "Device busy — could not acquire lock"
                self._finalize(item, result)
                return

            # Step 2: Navigate to the correct screen
            item.progress_step = "Navigating..."
            self._emit("task_progress", {
                "task_id": item.task_id, "serial": item.serial,
                "step": "Navigating to game screen..."
            })

            screen_map = {
                TaskType.PROFILE: "profile",
                TaskType.RESOURCES: "resources",
                TaskType.BUILDING: "hall",
                TaskType.HALL: "hall",
                TaskType.MARKET: "market",
                TaskType.PET: "pet",
            }
            screen = screen_map.get(item.task_type)
            if screen:
                navigator.navigate_to(item.serial, screen)

            # Step 3: Capture screenshot
            item.status = TaskStatus.CAPTURING
            item.progress_step = "Capturing..."
            self._emit("task_progress", {
                "task_id": item.task_id, "serial": item.serial,
                "step": "Capturing screenshot..."
            })

            img_path = emu.capture()
            if not img_path:
                result.status = TaskStatus.FAILED
                result.error = "Screenshot capture failed"
                self._finalize(item, result)
                return

            # Step 4: Load and process image
            item.status = TaskStatus.PROCESSING
            item.progress_step = "OCR Processing..."
            self._emit("task_progress", {
                "task_id": item.task_id, "serial": item.serial,
                "step": "Processing OCR..."
            })

            img = ocr_engine.load_image(img_path)
            if img is None:
                result.status = TaskStatus.FAILED
                result.error = "Failed to load screenshot"
                self._finalize(item, result)
                return

            # Step 5: Run OCR + Validate based on task type
            item.status = TaskStatus.VALIDATING
            data, val_result = self._process_scan(item.task_type, img)

            result.data = data
            result.validation_errors = val_result.errors if val_result else []
            result.is_reliable = val_result.is_reliable if val_result else False

            if val_result and val_result.is_valid:
                result.status = TaskStatus.SUCCESS
            else:
                result.status = TaskStatus.SUCCESS  # Still success, but flagged unreliable
                if not val_result or not val_result.is_valid:
                    result.is_reliable = False

            # Step 6: Navigate back
            if screen:
                navigator.go_back(item.serial, screen)

        except Exception as e:
            result.status = TaskStatus.FAILED
            result.error = str(e)
        finally:
            emu.release()
            self._finalize(item, result)

    def _process_scan(self, task_type: TaskType, img):
        """Run OCR and validation for a specific task type."""
        if task_type == TaskType.PROFILE:
            data = ocr_engine.scan_profile(img)
            val = validator.validate_profile(data)
            return data, val

        elif task_type == TaskType.RESOURCES:
            data = ocr_engine.scan_resources(img)
            val = validator.validate_resources(data)
            return data, val

        elif task_type in (TaskType.BUILDING, TaskType.HALL):
            level = ocr_engine.scan_building_level(img)
            val = validator.validate_building_level(level)
            return {"level": level}, val

        elif task_type == TaskType.MARKET:
            level = ocr_engine.scan_building_level(img)
            val = validator.validate_building_level(level)
            return {"level": level}, val

        elif task_type == TaskType.PET:
            token = ocr_engine.scan_pet_token(img)
            val = validator.validate_pet_token(token)
            return {"token": token}, val

        elif task_type == TaskType.FULL_SCAN:
            return self._full_scan(img)

        return {}, None

    def _full_scan(self, img):
        """Run all scans on a single screenshot (no navigation between)."""
        profile = ocr_engine.scan_profile(img)
        resources = ocr_engine.scan_resources(img)
        building = ocr_engine.scan_building_level(img)
        pet = ocr_engine.scan_pet_token(img)

        data = {
            "profile": profile,
            "resources": resources,
            "building": building,
            "pet_token": pet,
        }

        # Aggregate validation
        errors = []
        v1 = validator.validate_profile(profile)
        v2 = validator.validate_resources(resources)
        errors.extend(v1.errors)
        errors.extend(v2.errors)

        from backend.core.validator import ValidationResult
        combined = ValidationResult(
            is_valid=v1.is_valid and v2.is_valid,
            is_reliable=v1.is_reliable and v2.is_reliable,
            errors=errors,
        )
        return data, combined

    def _finalize(self, item: TaskQueueItem, result: TaskResult):
        """Finalize task: update timing, store history, emit event."""
        result.finished_at = datetime.now()
        if result.started_at:
            result.duration_ms = int(
                (result.finished_at - result.started_at).total_seconds() * 1000
            )

        # Remove from queue
        with self._lock:
            self._queue = [q for q in self._queue if q.task_id != item.task_id]

        # Add to history
        self._history.append(result)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        # Emit completion event
        event = "task_completed" if result.status == TaskStatus.SUCCESS else "task_failed"
        self._emit(event, result.model_dump(mode="json"))


# Global singleton
task_queue = TaskQueue()

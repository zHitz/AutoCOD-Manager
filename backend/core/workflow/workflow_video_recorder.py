import os
import shutil
import subprocess
import threading
import time
import uuid
from collections import deque
from pathlib import Path

import cv2

from backend.config import config


class _RecorderSession:
    def __init__(self, serial: str, capture_func, fps: float, buffer_seconds: int):
        self.serial = str(serial or "").strip()
        self.capture_func = capture_func
        self.fps = max(0.25, float(fps or 1.0))
        self.buffer_seconds = max(10, int(buffer_seconds or 45))
        self.max_frames = max(10, int(round(self.fps * self.buffer_seconds)))
        self.frames = deque(maxlen=self.max_frames)
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread = None
        self.started_at = time.time()

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(
            target=self._capture_loop,
            name=f"wf-recorder-{self.serial}",
            daemon=True,
        )
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3.0)

    def _capture_loop(self):
        interval = 1.0 / self.fps
        while not self.stop_event.is_set():
            loop_started = time.time()
            try:
                frame = self.capture_func()
                if frame is not None:
                    with self.lock:
                        self.frames.append((time.time(), frame.copy()))
            except Exception:
                pass

            elapsed = time.time() - loop_started
            remaining = interval - elapsed
            if remaining > 0:
                self.stop_event.wait(remaining)

    def snapshot_frames(self, include_final_frame: bool = True):
        frames = []
        with self.lock:
            frames.extend(list(self.frames))

        if include_final_frame:
            try:
                frame = self.capture_func()
                if frame is not None:
                    frames.append((time.time(), frame.copy()))
            except Exception:
                pass

        return frames


class WorkflowVideoRecorder:
    def __init__(self):
        self._sessions = {}
        self._active_by_serial = {}
        self._lock = threading.Lock()
        self._ffmpeg_path = self._find_ffmpeg_path()

    def _find_ffmpeg_path(self) -> str:
        candidates = [
            shutil.which("ffmpeg"),
            r"C:\Program Files\BlueStacks_nxt\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
        ]
        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                return candidate
        return ""

    def _transcode_browser_friendly(self, src_path: Path, dst_path: Path, fps: float) -> bool:
        if not self._ffmpeg_path or not src_path.exists():
            return False

        encoder_candidates = ["libx264", "h264_mf", "h264_nvenc", "h264_amf", "h264_qsv"]
        for encoder in encoder_candidates:
            cmd = [
                self._ffmpeg_path,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(src_path),
                "-an",
                "-c:v",
                encoder,
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                "-r",
                str(max(1.0, float(fps or 1.0))),
                str(dst_path),
            ]
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode == 0 and dst_path.exists() and dst_path.stat().st_size > 0:
                    return True
            except Exception:
                continue

            try:
                if dst_path.exists():
                    dst_path.unlink()
            except OSError:
                pass

        return False

    def start_session(
        self,
        serial: str,
        capture_func,
        fps: float = 1.0,
        buffer_seconds: int = 45,
    ) -> str:
        safe_serial = str(serial or "").strip()
        if not safe_serial or not callable(capture_func):
            return ""

        session_id = uuid.uuid4().hex
        session = _RecorderSession(
            serial=safe_serial,
            capture_func=capture_func,
            fps=fps,
            buffer_seconds=buffer_seconds,
        )

        with self._lock:
            existing_id = self._active_by_serial.get(safe_serial)
            if existing_id:
                existing = self._sessions.get(existing_id)
                if existing:
                    existing.stop()
                    self._sessions.pop(existing_id, None)
            self._sessions[session_id] = session
            self._active_by_serial[safe_serial] = session_id

        session.start()
        return session_id

    def discard_session(self, session_id: str):
        session = None
        with self._lock:
            session = self._sessions.pop(session_id, None)
            if session and self._active_by_serial.get(session.serial) == session_id:
                self._active_by_serial.pop(session.serial, None)

        if session:
            session.stop()

    def save_failure_clip(
        self,
        session_id: str,
        error_code: str = "",
        target_fps: float = 2.0,
    ) -> dict:
        session = None
        with self._lock:
            session = self._sessions.pop(session_id, None)
            if session and self._active_by_serial.get(session.serial) == session_id:
                self._active_by_serial.pop(session.serial, None)

        if not session:
            return {"video_path": "", "duration_ms": 0, "frame_count": 0}

        session.stop()
        frames = session.snapshot_frames(include_final_frame=True)
        if len(frames) < 2:
            return {"video_path": "", "duration_ms": 0, "frame_count": len(frames)}

        first_frame = frames[0][1]
        height, width = first_frame.shape[:2]
        if width <= 0 or height <= 0:
            return {"video_path": "", "duration_ms": 0, "frame_count": len(frames)}

        safe_tag = (str(error_code or "failure").split(":")[0].strip() or "failure").replace(" ", "_")
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        save_dir = Path(config.db_path).parent / "debug_captures" / session.serial
        os.makedirs(save_dir, exist_ok=True)
        out_path = save_dir / f"{timestamp}_{safe_tag}.mp4"
        raw_out_path = save_dir / f"{timestamp}_{safe_tag}.raw.mp4"

        fps = max(1.0, float(target_fps or session.fps or 1.0))
        writer = cv2.VideoWriter(
            str(raw_out_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (width, height),
        )
        if not writer.isOpened():
            return {"video_path": "", "duration_ms": 0, "frame_count": len(frames)}

        frame_count = 0
        try:
            for _, frame in frames:
                if frame is None:
                    continue
                if frame.shape[1] != width or frame.shape[0] != height:
                    frame = cv2.resize(frame, (width, height))
                writer.write(frame)
                frame_count += 1
        finally:
            writer.release()

        if frame_count <= 0:
            try:
                if raw_out_path.exists():
                    raw_out_path.unlink()
            except OSError:
                pass
            return {"video_path": "", "duration_ms": 0, "frame_count": 0}

        if self._transcode_browser_friendly(raw_out_path, out_path, fps):
            try:
                raw_out_path.unlink()
            except OSError:
                pass
        else:
            try:
                if out_path.exists():
                    out_path.unlink()
                raw_out_path.replace(out_path)
            except OSError:
                out_path = raw_out_path

        duration_ms = int((frame_count / fps) * 1000)
        return {
            "video_path": str(out_path),
            "duration_ms": duration_ms,
            "frame_count": frame_count,
        }


video_recorder = WorkflowVideoRecorder()

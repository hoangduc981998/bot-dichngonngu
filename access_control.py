"""Quản lý danh sách người dùng được phép dùng bot (lưu ra file JSON)."""
import json
import logging
import os
from threading import Lock

logger = logging.getLogger(__name__)


class AccessControl:
    def __init__(self, filepath: str, owner_id: int):
        self.filepath = filepath
        self.owner_id = owner_id
        self._lock = Lock()
        self.allowed: set[int] = set()
        self.pending: set[int] = set()
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.filepath):
            return
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.allowed = set(int(x) for x in data.get("allowed", []))
            self.pending = set(int(x) for x in data.get("pending", []))
            logger.info("Đã nạp %d user được duyệt.", len(self.allowed))
        except Exception as e:  # noqa: BLE001
            logger.error("Lỗi đọc file %s: %s", self.filepath, e)

    def _save(self) -> None:
        tmp = f"{self.filepath}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(
                {"allowed": sorted(self.allowed), "pending": sorted(self.pending)},
                f,
                ensure_ascii=False,
                indent=2,
            )
        os.replace(tmp, self.filepath)  # ghi nguyên tử, tránh hỏng file

    def is_allowed(self, user_id: int) -> bool:
        return user_id == self.owner_id or user_id in self.allowed

    def add_pending(self, user_id: int) -> None:
        with self._lock:
            self.pending.add(user_id)
            self._save()

    def approve(self, user_id: int) -> None:
        with self._lock:
            self.pending.discard(user_id)
            self.allowed.add(user_id)
            self._save()

    def reject(self, user_id: int) -> None:
        with self._lock:
            self.pending.discard(user_id)
            self.allowed.discard(user_id)
            self._save()

"""UUID-based asset tracking with TTL expiration."""

import logging
import os
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from .models import AssetRecord

logger = logging.getLogger(__name__)


def _make_key(filename: str, subfolder: str, folder_type: str) -> str:
    return f"{folder_type}:{subfolder}:{filename}"


class AssetRegistry:
    """In-memory asset registry with TTL-based expiration.

    Thread-safe via RLock. Uses (filename, subfolder, folder_type) as
    stable identity for deduplication.
    """

    def __init__(self, ttl_hours: int = 24, comfyui_base_url: str = "http://localhost:8188"):
        self._assets: dict[str, AssetRecord] = {}
        self._key_to_id: dict[str, str] = {}
        self._lock = threading.RLock()
        self.ttl_hours = ttl_hours
        self.comfyui_base_url = comfyui_base_url

    def register_asset(
        self,
        filename: str,
        subfolder: str,
        folder_type: str,
        workflow_id: str,
        prompt_id: str,
        mime_type: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        bytes_size: Optional[int] = None,
        comfy_history: Optional[dict[str, Any]] = None,
        submitted_workflow: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> AssetRecord:
        with self._lock:
            key = _make_key(filename, subfolder, folder_type)

            existing_id = self._key_to_id.get(key)
            if existing_id and existing_id in self._assets:
                existing = self._assets[existing_id]
                if existing.expires_at and datetime.now() > existing.expires_at:
                    del self._assets[existing_id]
                    del self._key_to_id[key]
                else:
                    if comfy_history is not None:
                        existing.comfy_history = comfy_history
                    if submitted_workflow is not None:
                        existing.submitted_workflow = submitted_workflow
                    return existing

            aid = str(uuid.uuid4())
            record = AssetRecord(
                asset_id=aid,
                filename=filename,
                subfolder=subfolder,
                folder_type=folder_type,
                prompt_id=prompt_id,
                workflow_id=workflow_id,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=self.ttl_hours),
                mime_type=mime_type or "application/octet-stream",
                width=width,
                height=height,
                bytes_size=bytes_size or 0,
                comfy_history=comfy_history,
                submitted_workflow=submitted_workflow,
                metadata=metadata or {},
                session_id=session_id,
            )
            record.set_base_url(self.comfyui_base_url)
            self._assets[aid] = record
            self._key_to_id[key] = aid
            return record

    def get_asset(self, asset_id: str) -> Optional[AssetRecord]:
        with self._lock:
            record = self._assets.get(asset_id)
            if not record:
                return None
            if record.expires_at and datetime.now() > record.expires_at:
                key = _make_key(record.filename, record.subfolder, record.folder_type)
                del self._assets[asset_id]
                self._key_to_id.pop(key, None)
                return None
            return record

    def get_asset_by_identity(
        self, filename: str, subfolder: str, folder_type: str
    ) -> Optional[AssetRecord]:
        with self._lock:
            aid = self._key_to_id.get(_make_key(filename, subfolder, folder_type))
            return self.get_asset(aid) if aid else None

    def list_assets(
        self,
        limit: int = 10,
        workflow_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> list[AssetRecord]:
        with self._lock:
            self.cleanup_expired()
            assets = list(self._assets.values())
            if workflow_id:
                assets = [a for a in assets if a.workflow_id == workflow_id]
            if session_id:
                assets = [a for a in assets if a.session_id == session_id]
            assets.sort(key=lambda a: a.created_at, reverse=True)
            return assets[:limit]

    def cleanup_expired(self) -> int:
        with self._lock:
            now = datetime.now()
            expired = [
                aid for aid, r in self._assets.items()
                if r.expires_at and now > r.expires_at
            ]
            for aid in expired:
                r = self._assets[aid]
                self._key_to_id.pop(
                    _make_key(r.filename, r.subfolder, r.folder_type), None
                )
                del self._assets[aid]
            return len(expired)

    def get_asset_local_path(self, asset_id: str) -> Optional[str]:
        record = self.get_asset(asset_id)
        if not record:
            return None

        root = os.getenv("COMFYUI_OUTPUT_ROOT")
        if root:
            base = Path(root)
        else:
            for candidate in (
                Path.home() / "ComfyUI" / "output",
                Path("C:/ComfyUI/output"),
                Path("/opt/ComfyUI/output"),
            ):
                if candidate.exists():
                    base = candidate
                    break
            else:
                return None

        if record.subfolder:
            p = base / record.subfolder / record.filename
        else:
            p = base / record.filename
        if p.exists():
            return str(p)
        p2 = base / record.filename
        return str(p2) if p2.exists() else None

"""Asset data models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from urllib.parse import quote


@dataclass
class AssetRecord:
    """Record of a generated asset.

    Uses (filename, subfolder, folder_type) as stable identity rather than
    URL, making the system robust to hostname/port changes.
    """

    asset_id: str
    filename: str
    subfolder: str
    folder_type: str  # usually "output"
    prompt_id: str
    workflow_id: str
    created_at: datetime
    expires_at: Optional[datetime]

    mime_type: str
    width: Optional[int]
    height: Optional[int]
    bytes_size: int
    sha256: Optional[str] = None

    comfy_history: Optional[dict[str, Any]] = field(default=None)
    submitted_workflow: Optional[dict[str, Any]] = field(default=None)
    metadata: dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None

    def get_asset_url(self, base_url: str) -> str:
        base_url = base_url.rstrip("/")
        enc_fn = quote(self.filename, safe="")
        enc_sf = quote(self.subfolder, safe="") if self.subfolder else ""
        url = f"{base_url}/view?filename={enc_fn}"
        if enc_sf:
            url += f"&subfolder={enc_sf}"
        url += f"&type={self.folder_type}"
        return url

    @property
    def asset_url(self) -> str:
        base = getattr(self, "_base_url", None)
        return self.get_asset_url(base) if base else ""

    def set_base_url(self, base_url: str) -> None:
        self._base_url = base_url

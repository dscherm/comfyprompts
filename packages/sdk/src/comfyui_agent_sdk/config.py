"""Centralized configuration for ComfyUI Agent SDK."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ComfyUIConfig:
    """Configuration for connecting to and working with ComfyUI.

    Values are resolved in order: explicit argument > environment variable > default.
    """

    # ComfyUI server connection
    comfyui_url: str = ""
    generation_timeout: int = 300
    max_retries: int = 5
    initial_retry_delay: float = 2.0
    max_retry_delay: float = 16.0

    # ComfyUI installation paths
    comfyui_path: Optional[str] = None
    output_root: Optional[str] = None

    # Model folder paths (auto-derived from comfyui_path if not set)
    model_folders: dict[str, str] = field(default_factory=dict)

    # Workflow configuration
    workflow_dir: Optional[str] = None

    # Asset registry
    asset_ttl_hours: int = 24

    # MCP server
    mcp_port: int = 9000
    mcp_transport: str = "streamable-http"

    # Ollama (for recommender)
    ollama_url: str = ""
    ollama_model: str = "llama3.2"

    def __post_init__(self):
        # Resolve from environment if not explicitly set
        if not self.comfyui_url:
            self.comfyui_url = os.getenv("COMFYUI_URL", "http://localhost:8188")
        self.comfyui_url = self.comfyui_url.rstrip("/")

        self.generation_timeout = int(
            os.getenv("COMFY_MCP_GENERATION_TIMEOUT", str(self.generation_timeout))
        )
        self.asset_ttl_hours = int(
            os.getenv("COMFY_MCP_ASSET_TTL_HOURS", str(self.asset_ttl_hours))
        )
        self.mcp_port = int(os.getenv("COMFY_MCP_PORT", str(self.mcp_port)))

        if not self.comfyui_path:
            self.comfyui_path = os.getenv("COMFYUI_PATH")
        if not self.output_root:
            self.output_root = os.getenv("COMFYUI_OUTPUT_ROOT")
        if not self.workflow_dir:
            self.workflow_dir = os.getenv(
                "COMFY_MCP_WORKFLOW_DIR",
                str(Path(__file__).parent.parent.parent / "workflows"),
            )
        if not self.ollama_url:
            self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", self.ollama_model)

        # Build default model folders from comfyui_path
        if not self.model_folders and self.comfyui_path:
            base = Path(self.comfyui_path) / "models"
            self.model_folders = {
                "checkpoints": str(base / "checkpoints"),
                "diffusion_models": str(base / "diffusion_models"),
                "vae": str(base / "vae"),
                "clip": str(base / "clip"),
                "text_encoders": str(base / "text_encoders"),
                "controlnet": str(base / "controlnet"),
                "upscale_models": str(base / "upscale_models"),
                "loras": str(base / "loras"),
                "diffusers": str(base / "diffusers"),
                "tts": str(base / "tts"),
            }

    @property
    def workflow_path(self) -> Path:
        return Path(self.workflow_dir)

    def get_model_folder(self, model_type: str) -> Optional[Path]:
        """Get the filesystem path for a model type folder."""
        folder = self.model_folders.get(model_type)
        if folder:
            return Path(folder)
        return None

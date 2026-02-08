"""Tripo3D API client for cloud-based rigging and animation.

Uses the official Tripo3D Python SDK for AI-powered:
- Auto-rigging (skeleton generation + skinning)
- Animation (preset animations applied to rigged models)
- Model generation (text/image to 3D)

Requires: pip install tripo3d
API Key: Get from https://platform.tripo3d.ai/
"""

import asyncio
import json
import logging
import os
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("MCP_Server")

# Base API URL
TRIPO_API_BASE = "https://api.tripo3d.ai/v2/openapi"


class TripoTaskStatus(Enum):
    """Status of a Tripo3D task."""
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class TripoAnimationPreset(Enum):
    """Available animation presets from Tripo3D."""
    IDLE = "preset:idle"
    WALK = "preset:walk"
    RUN = "preset:run"
    JUMP = "preset:jump"
    DANCE = "preset:dance"
    WAVE = "preset:wave"
    ATTACK = "preset:attack"
    DIE = "preset:die"


@dataclass
class TripoTask:
    """Represents a Tripo3D task result."""
    task_id: str
    status: TripoTaskStatus
    progress: int
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    @property
    def model_url(self) -> Optional[str]:
        """Get the model download URL."""
        if self.output and "model" in self.output:
            return self.output["model"].get("url")
        return None

    @property
    def rigged_model_url(self) -> Optional[str]:
        """Get the rigged model download URL."""
        if self.output and "rig" in self.output:
            return self.output["rig"].get("url")
        return None

    @property
    def animated_model_url(self) -> Optional[str]:
        """Get the animated model download URL."""
        if self.output and "rendered_image" in self.output:
            # Animation output varies
            return self.output.get("rendered_image", {}).get("url")
        return None


class TripoClient:
    """Client for Tripo3D API.

    Provides methods for:
    - Auto-rigging 3D models
    - Applying animation presets
    - Text/Image to 3D generation

    Example:
        client = TripoClient(api_key="your_key")

        # Rig a model
        result = await client.rig_model("path/to/model.glb")

        # Animate a rigged model
        result = await client.animate_model(
            "path/to/rigged.glb",
            animation="preset:walk"
        )
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Tripo3D client.

        Args:
            api_key: Tripo3D API key. If not provided, reads from
                     TRIPO_API_KEY environment variable.
        """
        self.api_key = api_key or os.getenv("TRIPO_API_KEY")
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def is_configured(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=TRIPO_API_BASE,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=300.0  # 5 minute timeout for long operations
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=TRIPO_API_BASE,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=300.0
            )
        return self._client

    async def _poll_task(
        self,
        task_id: str,
        poll_interval: float = 2.0,
        max_wait: float = 300.0
    ) -> TripoTask:
        """Poll a task until completion.

        Args:
            task_id: Task ID to poll
            poll_interval: Seconds between polls
            max_wait: Maximum seconds to wait

        Returns:
            Completed task result
        """
        client = self._get_client()
        elapsed = 0.0

        while elapsed < max_wait:
            response = await client.get(f"/task/{task_id}")
            response.raise_for_status()
            data = response.json()["data"]

            status = TripoTaskStatus(data.get("status", "unknown"))
            task = TripoTask(
                task_id=task_id,
                status=status,
                progress=data.get("progress", 0),
                output=data.get("output"),
                error=data.get("error")
            )

            if status in (TripoTaskStatus.SUCCESS, TripoTaskStatus.FAILED,
                         TripoTaskStatus.CANCELLED):
                return task

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        return TripoTask(
            task_id=task_id,
            status=TripoTaskStatus.UNKNOWN,
            progress=0,
            error="Task polling timed out"
        )

    async def upload_model(self, file_path: Path) -> str:
        """Upload a 3D model file to Tripo3D.

        Args:
            file_path: Path to model file (GLB, FBX, OBJ)

        Returns:
            File token for use in other API calls
        """
        client = self._get_client()

        # Get upload URL
        response = await client.post("/upload", json={
            "type": "model"
        })
        response.raise_for_status()
        upload_data = response.json()["data"]

        # Upload file
        upload_url = upload_data["upload_url"]
        file_token = upload_data["file_token"]

        with open(file_path, "rb") as f:
            async with httpx.AsyncClient() as upload_client:
                await upload_client.put(
                    upload_url,
                    content=f.read(),
                    headers={"Content-Type": "application/octet-stream"}
                )

        return file_token

    async def rig_model(
        self,
        model_path: Path,
        output_format: str = "glb",
        wait: bool = True
    ) -> Dict[str, Any]:
        """Auto-rig a 3D model with AI.

        Creates a skeleton and skin weights for animation.

        Args:
            model_path: Path to 3D model file (GLB, FBX, OBJ)
            output_format: Output format (glb, fbx)
            wait: Wait for task completion

        Returns:
            Dict with task_id, status, and output URLs
        """
        if not self.is_configured:
            return {"error": "Tripo3D API key not configured. Set TRIPO_API_KEY environment variable."}

        model_path = Path(model_path)
        if not model_path.exists():
            return {"error": f"Model file not found: {model_path}"}

        try:
            client = self._get_client()

            # Upload the model
            logger.info(f"Uploading model to Tripo3D: {model_path}")
            file_token = await self.upload_model(model_path)

            # Start rigging task
            logger.info("Starting auto-rig task...")
            response = await client.post("/task", json={
                "type": "rig",
                "file": {
                    "type": "model",
                    "file_token": file_token
                },
                "out_format": output_format
            })
            response.raise_for_status()
            task_id = response.json()["data"]["task_id"]

            if not wait:
                return {
                    "success": True,
                    "task_id": task_id,
                    "status": "queued",
                    "message": "Rigging task started"
                }

            # Poll for completion
            logger.info(f"Waiting for rigging task: {task_id}")
            task = await self._poll_task(task_id)

            if task.status == TripoTaskStatus.SUCCESS:
                return {
                    "success": True,
                    "task_id": task_id,
                    "status": "success",
                    "rigged_model_url": task.rigged_model_url or task.model_url,
                    "output": task.output,
                    "message": "Model rigged successfully"
                }
            else:
                return {
                    "error": f"Rigging failed: {task.error}",
                    "task_id": task_id,
                    "status": task.status.value
                }

        except httpx.HTTPStatusError as e:
            logger.exception(f"Tripo3D API error: {e}")
            return {"error": f"API error: {e.response.status_code} - {e.response.text}"}
        except Exception as e:
            logger.exception(f"Failed to rig model: {e}")
            return {"error": str(e)}

    async def animate_model(
        self,
        model_path: Path,
        animation: str = "preset:walk",
        output_format: str = "glb",
        wait: bool = True
    ) -> Dict[str, Any]:
        """Apply animation to a rigged model.

        Args:
            model_path: Path to rigged 3D model (GLB, FBX)
            animation: Animation preset or custom animation ID
                       Presets: preset:idle, preset:walk, preset:run,
                               preset:jump, preset:dance, preset:wave
            output_format: Output format (glb, fbx)
            wait: Wait for task completion

        Returns:
            Dict with task_id, status, and output URLs
        """
        if not self.is_configured:
            return {"error": "Tripo3D API key not configured. Set TRIPO_API_KEY environment variable."}

        model_path = Path(model_path)
        if not model_path.exists():
            return {"error": f"Model file not found: {model_path}"}

        try:
            client = self._get_client()

            # Upload the model
            logger.info(f"Uploading model for animation: {model_path}")
            file_token = await self.upload_model(model_path)

            # Start animation task
            logger.info(f"Starting animation task with preset: {animation}")
            response = await client.post("/task", json={
                "type": "animate",
                "file": {
                    "type": "model",
                    "file_token": file_token
                },
                "animation": animation,
                "out_format": output_format
            })
            response.raise_for_status()
            task_id = response.json()["data"]["task_id"]

            if not wait:
                return {
                    "success": True,
                    "task_id": task_id,
                    "status": "queued",
                    "animation": animation,
                    "message": "Animation task started"
                }

            # Poll for completion
            logger.info(f"Waiting for animation task: {task_id}")
            task = await self._poll_task(task_id)

            if task.status == TripoTaskStatus.SUCCESS:
                return {
                    "success": True,
                    "task_id": task_id,
                    "status": "success",
                    "animation": animation,
                    "animated_model_url": task.animated_model_url or task.model_url,
                    "output": task.output,
                    "message": f"Animation '{animation}' applied successfully"
                }
            else:
                return {
                    "error": f"Animation failed: {task.error}",
                    "task_id": task_id,
                    "status": task.status.value
                }

        except httpx.HTTPStatusError as e:
            logger.exception(f"Tripo3D API error: {e}")
            return {"error": f"API error: {e.response.status_code} - {e.response.text}"}
        except Exception as e:
            logger.exception(f"Failed to animate model: {e}")
            return {"error": str(e)}

    async def rig_and_animate(
        self,
        model_path: Path,
        animation: str = "preset:walk",
        output_format: str = "glb",
        output_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Rig a model and apply animation in one workflow.

        Args:
            model_path: Path to 3D model file
            animation: Animation preset to apply
            output_format: Output format (glb, fbx)
            output_dir: Directory to save output files

        Returns:
            Dict with paths to rigged and animated models
        """
        # First, rig the model
        rig_result = await self.rig_model(model_path, output_format)
        if "error" in rig_result:
            return rig_result

        # Download rigged model
        rigged_url = rig_result.get("rigged_model_url")
        if not rigged_url:
            return {"error": "No rigged model URL in response"}

        output_dir = output_dir or Path(tempfile.gettempdir()) / "tripo_output"
        output_dir.mkdir(parents=True, exist_ok=True)

        rigged_path = output_dir / f"{model_path.stem}_rigged.{output_format}"

        async with httpx.AsyncClient() as download_client:
            response = await download_client.get(rigged_url)
            response.raise_for_status()
            with open(rigged_path, "wb") as f:
                f.write(response.content)

        # Then animate
        anim_result = await self.animate_model(rigged_path, animation, output_format)
        if "error" in anim_result:
            return {
                "partial_success": True,
                "rigged_path": str(rigged_path),
                "animation_error": anim_result["error"]
            }

        # Download animated model
        animated_url = anim_result.get("animated_model_url")
        if animated_url:
            animated_path = output_dir / f"{model_path.stem}_{animation.replace(':', '_')}.{output_format}"
            async with httpx.AsyncClient() as download_client:
                response = await download_client.get(animated_url)
                response.raise_for_status()
                with open(animated_path, "wb") as f:
                    f.write(response.content)

            return {
                "success": True,
                "rigged_path": str(rigged_path),
                "animated_path": str(animated_path),
                "animation": animation,
                "message": f"Model rigged and animated with {animation}"
            }

        return {
            "success": True,
            "rigged_path": str(rigged_path),
            "animation": animation,
            "message": "Model rigged, animation applied (check task output for download)"
        }

    async def get_balance(self) -> Dict[str, Any]:
        """Get account balance/credits.

        Returns:
            Dict with balance information
        """
        if not self.is_configured:
            return {"error": "Tripo3D API key not configured"}

        try:
            client = self._get_client()
            response = await client.get("/user/balance")
            response.raise_for_status()
            return response.json()["data"]
        except Exception as e:
            return {"error": str(e)}

    def list_animation_presets(self) -> List[Dict[str, str]]:
        """List available animation presets.

        Returns:
            List of animation preset info
        """
        return [
            {"id": "preset:idle", "name": "Idle", "description": "Standing idle animation"},
            {"id": "preset:walk", "name": "Walk", "description": "Walking cycle"},
            {"id": "preset:run", "name": "Run", "description": "Running cycle"},
            {"id": "preset:jump", "name": "Jump", "description": "Jump animation"},
            {"id": "preset:dance", "name": "Dance", "description": "Dance animation"},
            {"id": "preset:wave", "name": "Wave", "description": "Waving gesture"},
            {"id": "preset:attack", "name": "Attack", "description": "Attack/combat animation"},
            {"id": "preset:die", "name": "Die", "description": "Death animation"},
        ]


# Synchronous wrapper for non-async contexts
class TripoClientSync:
    """Synchronous wrapper for TripoClient."""

    def __init__(self, api_key: Optional[str] = None):
        self._async_client = TripoClient(api_key)

    @property
    def is_configured(self) -> bool:
        return self._async_client.is_configured

    def _run(self, coro):
        """Run async coroutine synchronously."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)

    def rig_model(self, model_path: Path, **kwargs) -> Dict[str, Any]:
        return self._run(self._async_client.rig_model(model_path, **kwargs))

    def animate_model(self, model_path: Path, **kwargs) -> Dict[str, Any]:
        return self._run(self._async_client.animate_model(model_path, **kwargs))

    def rig_and_animate(self, model_path: Path, **kwargs) -> Dict[str, Any]:
        return self._run(self._async_client.rig_and_animate(model_path, **kwargs))

    def get_balance(self) -> Dict[str, Any]:
        return self._run(self._async_client.get_balance())

    def list_animation_presets(self) -> List[Dict[str, str]]:
        return self._async_client.list_animation_presets()

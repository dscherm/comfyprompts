"""Unified REST client for ComfyUI, merged from comfyui-mcp-server and comfyui-prompter."""

import json
import logging
import time
import uuid
from typing import Any, Optional, Sequence
from urllib.parse import quote

import requests

from ..config import ComfyUIConfig
from .errors import (
    ComfyUIError,
    parse_comfyui_error,
    parse_execution_error,
    raise_for_node_errors,
)

logger = logging.getLogger(__name__)


class ComfyUIClient:
    """Unified ComfyUI REST client.

    Combines the MCP server's workflow-execution client with the prompter's
    queue management, introspection, and history features.
    """

    def __init__(self, config: ComfyUIConfig | None = None, *, base_url: str | None = None, default_timeout: int | None = None):
        if config is None:
            config = ComfyUIConfig()
        self.config = config
        self.base_url = (base_url or config.comfyui_url).rstrip("/")
        self.default_timeout = default_timeout or config.generation_timeout
        self.client_id = str(uuid.uuid4())
        self.available_models: list[str] = []
        self._refresh_models()

    # ------------------------------------------------------------------
    # Connection / health
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/system_stats", timeout=5)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def check_connection(self) -> dict:
        try:
            r = requests.get(f"{self.base_url}/system_stats", timeout=5)
            if r.status_code == 200:
                stats = r.json()
                dev = stats.get("devices", [{}])[0]
                return {
                    "connected": True,
                    "vram_total": dev.get("vram_total"),
                    "vram_free": dev.get("vram_free"),
                }
            return {"connected": False, "error": f"HTTP {r.status_code}"}
        except requests.RequestException as e:
            return {"connected": False, "error": str(e)}

    def get_system_stats(self) -> dict | None:
        try:
            r = requests.get(f"{self.base_url}/system_stats", timeout=5)
            return r.json() if r.status_code == 200 else None
        except requests.RequestException:
            return None

    # ------------------------------------------------------------------
    # Models
    # ------------------------------------------------------------------

    def refresh_models(self) -> None:
        self._refresh_models()

    def _refresh_models(self) -> None:
        self.available_models = self._get_available_models()

    def _get_available_models(self) -> list[str]:
        try:
            r = requests.get(f"{self.base_url}/object_info/CheckpointLoaderSimple", timeout=10)
            if r.status_code != 200:
                return []
            data = r.json()
            info = (
                data.get("CheckpointLoaderSimple", {})
                .get("input", {})
                .get("required", {})
                .get("ckpt_name", [])
            )
            if isinstance(info, list) and info:
                return info[0] if isinstance(info[0], list) else info
            return []
        except Exception as e:
            logger.warning("Error fetching models: %s", e)
            return []

    def _get_models_from_object_info(self, node_class: str, param_name: str) -> list[str]:
        """Generic helper to query model lists from ComfyUI's /object_info endpoint.

        Args:
            node_class: The node class to query (e.g., "LoraLoader", "VAELoader").
            param_name: The parameter name containing the model list (e.g., "lora_name").

        Returns:
            List of available model filenames, or empty list on failure.
        """
        try:
            r = requests.get(f"{self.base_url}/object_info/{node_class}", timeout=10)
            if r.status_code != 200:
                return []
            info = (
                r.json()
                .get(node_class, {})
                .get("input", {})
                .get("required", {})
                .get(param_name, [])
            )
            if isinstance(info, list) and info:
                return info[0] if isinstance(info[0], list) else info
            return []
        except Exception:
            return []

    def get_upscale_models(self) -> list[str]:
        return self._get_models_from_object_info("UpscaleModelLoader", "model_name")

    def get_lora_models(self) -> list[str]:
        return self._get_models_from_object_info("LoraLoader", "lora_name")

    def get_controlnet_models(self) -> list[str]:
        return self._get_models_from_object_info("ControlNetLoader", "control_net_name")

    def get_vae_models(self) -> list[str]:
        return self._get_models_from_object_info("VAELoader", "vae_name")

    # ------------------------------------------------------------------
    # Workflow execution (from mcp-server)
    # ------------------------------------------------------------------

    def run_custom_workflow(
        self,
        workflow: dict[str, Any],
        preferred_output_keys: Sequence[str] | None = None,
        max_attempts: int | None = None,
    ) -> dict:
        if preferred_output_keys is None:
            preferred_output_keys = (
                "images", "image", "gifs", "gif", "audio", "audios", "files",
            )
        if max_attempts is None:
            max_attempts = self.default_timeout

        prompt_id = self._queue_workflow(workflow)
        outputs = self._wait_for_prompt(prompt_id, max_attempts=max_attempts)

        asset_info = self._extract_first_asset_info(outputs, preferred_output_keys)
        asset_url = asset_info["asset_url"]
        asset_metadata = self._get_asset_metadata(
            asset_url, outputs, preferred_output_keys, workflow
        )

        try:
            history = self.get_history(prompt_id)
            comfy_history = history.get(prompt_id, {}) if history else {}
        except Exception:
            comfy_history = None

        return {
            "asset_url": asset_url,
            "filename": asset_info["filename"],
            "subfolder": asset_info["subfolder"],
            "folder_type": asset_info["type"],
            "prompt_id": prompt_id,
            "raw_outputs": outputs,
            "asset_metadata": asset_metadata,
            "comfy_history": comfy_history,
            "submitted_workflow": workflow,
        }

    # ------------------------------------------------------------------
    # Queue management (merged from both projects)
    # ------------------------------------------------------------------

    def queue_prompt(self, workflow: dict) -> dict | None:
        """Queue a workflow and return the response (prompt_id, number, etc.)."""
        try:
            r = requests.post(
                f"{self.base_url}/prompt",
                json={"prompt": workflow, "client_id": self.client_id},
                timeout=30,
            )
            if r.status_code == 200:
                return r.json()
            logger.warning("Failed to queue prompt: %s", r.status_code)
            return None
        except requests.RequestException as e:
            logger.error("Error queueing prompt: %s", e)
            return None

    def get_queue(self) -> dict:
        try:
            r = requests.get(f"{self.base_url}/queue", timeout=10)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            raise ComfyUIError(f"Failed to get queue status: {e}")

    def get_queue_info(self) -> dict:
        """Structured queue info with running/pending lists."""
        result: dict[str, Any] = {
            "running": [], "pending": [],
            "running_count": 0, "pending_count": 0,
        }
        try:
            qs = self.get_queue()
            for item in qs.get("queue_running", []):
                if len(item) >= 2:
                    result["running"].append({
                        "number": item[0], "prompt_id": item[1],
                        "prompt": item[2] if len(item) > 2 else {},
                    })
            for item in qs.get("queue_pending", []):
                if len(item) >= 2:
                    result["pending"].append({
                        "number": item[0], "prompt_id": item[1],
                        "prompt": item[2] if len(item) > 2 else {},
                    })
            result["running_count"] = len(result["running"])
            result["pending_count"] = len(result["pending"])
        except Exception as e:
            logger.error("Error getting queue info: %s", e)
        return result

    def interrupt_execution(self) -> bool:
        try:
            r = requests.post(f"{self.base_url}/interrupt", timeout=5)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def clear_queue(self) -> bool:
        try:
            r = requests.post(f"{self.base_url}/queue", json={"clear": True}, timeout=5)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def cancel_prompt(self, prompt_id: str) -> dict:
        try:
            r = requests.post(
                f"{self.base_url}/queue",
                json={"delete": [prompt_id]},
                timeout=10,
            )
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            raise ComfyUIError(f"Failed to cancel prompt: {e}")

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def get_history(self, prompt_id: str | None = None) -> dict:
        try:
            url = f"{self.base_url}/history"
            if prompt_id:
                url = f"{url}/{prompt_id}"
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            raise ComfyUIError(f"Failed to get history: {e}")

    def delete_history_item(self, prompt_id: str) -> bool:
        try:
            r = requests.post(
                f"{self.base_url}/history",
                json={"delete": [prompt_id]},
                timeout=5,
            )
            return r.status_code == 200
        except requests.RequestException:
            return False

    def clear_history(self) -> bool:
        try:
            r = requests.post(
                f"{self.base_url}/history", json={"clear": True}, timeout=5
            )
            return r.status_code == 200
        except requests.RequestException:
            return False

    # ------------------------------------------------------------------
    # Introspection (from prompter)
    # ------------------------------------------------------------------

    def get_object_info(self, node_type: str | None = None) -> dict | None:
        """Get node definitions from ComfyUI /object_info."""
        try:
            url = f"{self.base_url}/object_info"
            if node_type:
                url = f"{url}/{node_type}"
            r = requests.get(url, timeout=30)
            return r.json() if r.status_code == 200 else None
        except requests.RequestException:
            return None

    # ------------------------------------------------------------------
    # Image upload
    # ------------------------------------------------------------------

    def upload_image(
        self, image_bytes: bytes, filename: str, subfolder: str = "", overwrite: bool = True
    ) -> dict:
        try:
            files = {"image": (filename, image_bytes, "image/png")}
            data: dict[str, str] = {"overwrite": str(overwrite).lower()}
            if subfolder:
                data["subfolder"] = subfolder
            r = requests.post(
                f"{self.base_url}/upload/image", files=files, data=data, timeout=60
            )
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            raise ComfyUIError(f"Failed to upload image: {e}")

    # ------------------------------------------------------------------
    # Job status (from prompter)
    # ------------------------------------------------------------------

    def get_job_status(self, prompt_id: str) -> dict:
        result: dict[str, Any] = {
            "status": "pending", "progress": 0.0, "outputs": [], "error": None
        }
        try:
            history = self.get_history(prompt_id)
        except Exception:
            history = {}

        if history and prompt_id in history:
            result["status"] = "completed"
            result["progress"] = 100.0
            outputs = history[prompt_id].get("outputs", {})
            result["outputs"] = self._extract_output_paths(outputs)
            return result

        try:
            qs = self.get_queue()
        except Exception:
            result["status"] = "error"
            result["error"] = "Cannot reach ComfyUI"
            return result

        for item in qs.get("queue_running", []):
            if len(item) > 1 and item[1] == prompt_id:
                result["status"] = "running"
                result["progress"] = 50.0
                return result

        for item in qs.get("queue_pending", []):
            if len(item) > 1 and item[1] == prompt_id:
                result["status"] = "pending"
                return result

        result["status"] = "error"
        result["error"] = "Job not found in queue or history"
        return result

    def wait_for_completion(self, prompt_id: str, timeout: int = 300) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            status = self.get_job_status(prompt_id)
            if status["status"] == "completed":
                return True
            if status["status"] == "error":
                return False
            time.sleep(2)
        return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _queue_workflow(self, workflow: dict) -> str:
        if not self.is_available():
            raise ComfyUIError("ComfyUI is not responding. Ensure ComfyUI is running.")

        try:
            r = requests.post(
                f"{self.base_url}/prompt", json={"prompt": workflow}, timeout=30
            )
        except requests.RequestException as e:
            raise ComfyUIError(f"Failed to connect to ComfyUI: {e}")

        if r.status_code != 200:
            try:
                err = r.json()
                if "error" in err:
                    raise ComfyUIError(parse_comfyui_error(err["error"]))
                if "node_errors" in err:
                    raise_for_node_errors(err)
            except json.JSONDecodeError:
                pass
            raise ComfyUIError(
                f"Failed to queue workflow: {r.status_code} - {r.text[:500]}"
            )

        data = r.json()
        prompt_id = data.get("prompt_id")
        if not prompt_id:
            raise ComfyUIError("Response missing prompt_id")
        logger.info("Queued workflow with prompt_id: %s", prompt_id)
        return prompt_id

    def _wait_for_prompt(self, prompt_id: str, max_attempts: int = 300) -> dict:
        for attempt in range(max_attempts):
            try:
                r = requests.get(f"{self.base_url}/history/{prompt_id}", timeout=10)
                if r.status_code != 200:
                    time.sleep(1)
                    continue

                history = r.json()
                if not isinstance(history, dict) or prompt_id not in history:
                    time.sleep(1)
                    continue

                prompt_data = history[prompt_id]
                if not isinstance(prompt_data, dict):
                    time.sleep(1)
                    continue

                # Check for error in prompt data
                if "error" in prompt_data:
                    raise ComfyUIError(
                        f"Workflow failed: {parse_comfyui_error(prompt_data['error'])}"
                    )

                # Check status for failures
                status = prompt_data.get("status", {})
                if isinstance(status, dict):
                    status_str = status.get("status_str", "")
                    if status_str == "error" or status.get("completed") is False:
                        messages = status.get("messages", [])
                        for msg in messages:
                            if isinstance(msg, list) and len(msg) > 1:
                                if msg[0] == "execution_error" and isinstance(msg[1], dict):
                                    raise ComfyUIError(parse_execution_error(msg[1]))
                        raise ComfyUIError(f"Workflow failed: {messages}")

                # Extract outputs
                if "outputs" not in prompt_data:
                    # Check if execution succeeded but outputs not ready yet
                    if isinstance(status, dict):
                        msgs = status.get("messages", [])
                        for m in msgs:
                            if isinstance(m, list) and m and m[0] == "execution_success":
                                time.sleep(3)
                                break
                    time.sleep(1)
                    continue

                outputs = prompt_data["outputs"]
                if not outputs or not isinstance(outputs, dict):
                    time.sleep(1)
                    continue

                logger.info("Workflow completed. Output nodes: %s", list(outputs.keys()))
                return outputs

            except requests.RequestException:
                time.sleep(1)
            except (ValueError, KeyError):
                time.sleep(1)

        raise ComfyUIError(
            f"Workflow {prompt_id} timed out after {max_attempts} seconds. "
            "Increase COMFY_MCP_GENERATION_TIMEOUT for slow models."
        )

    def _extract_first_asset_info(
        self, outputs: dict, preferred_output_keys: Sequence[str]
    ) -> dict:
        for node_id, node_output in outputs.items():
            if not isinstance(node_output, dict):
                continue
            for key in preferred_output_keys:
                assets = node_output.get(key)
                if assets and isinstance(assets, list) and assets:
                    asset = assets[0]
                    if not isinstance(asset, dict):
                        continue
                    filename = asset.get("filename")
                    if not filename:
                        continue
                    subfolder = asset.get("subfolder", "")
                    output_type = asset.get("type", "output")

                    enc_fn = quote(filename, safe="")
                    enc_sf = quote(subfolder, safe="") if subfolder else ""
                    url = f"{self.base_url}/view?filename={enc_fn}"
                    if enc_sf:
                        url += f"&subfolder={enc_sf}"
                    url += f"&type={output_type}"

                    return {
                        "filename": filename,
                        "subfolder": subfolder,
                        "type": output_type,
                        "asset_url": url,
                    }

        raise ComfyUIError(
            f"No outputs matched preferred keys: {preferred_output_keys}. "
            f"Available: {json.dumps({k: list(v.keys()) if isinstance(v, dict) else type(v).__name__ for k, v in outputs.items()})}"
        )

    def _get_asset_metadata(
        self,
        asset_url: str,
        outputs: dict,
        preferred_output_keys: Sequence[str],
        workflow: dict | None = None,
    ) -> dict:
        metadata: dict[str, Any] = {
            "mime_type": None, "width": None, "height": None, "bytes_size": None
        }

        # Infer mime from output filename
        for node_output in outputs.values():
            if not isinstance(node_output, dict):
                continue
            for key in preferred_output_keys:
                assets = node_output.get(key)
                if assets and isinstance(assets, list) and assets:
                    fn = assets[0].get("filename", "") if isinstance(assets[0], dict) else ""
                    mime = _mime_from_filename(fn)
                    if mime:
                        metadata["mime_type"] = mime
                        break
            if metadata["mime_type"]:
                break

        # Dimensions from workflow EmptyLatentImage
        if workflow:
            for node_data in workflow.values():
                if not isinstance(node_data, dict):
                    continue
                if node_data.get("class_type") == "EmptyLatentImage":
                    inputs = node_data.get("inputs", {})
                    metadata.setdefault("width", inputs.get("width"))
                    metadata.setdefault("height", inputs.get("height"))
                    if metadata["width"] and metadata["height"]:
                        break

        # HEAD request for size
        try:
            r = requests.head(asset_url, timeout=5)
            if r.status_code == 200:
                cl = r.headers.get("Content-Length")
                if cl:
                    metadata["bytes_size"] = int(cl)
                ct = r.headers.get("Content-Type")
                if ct and not metadata["mime_type"]:
                    metadata["mime_type"] = ct.split(";")[0].strip()
        except Exception:
            pass

        # Fallback: fetch image bytes for dimensions
        if (
            metadata["mime_type"]
            and metadata["mime_type"].startswith("image/")
            and (metadata["width"] is None or metadata["height"] is None)
        ):
            try:
                r = requests.get(asset_url, timeout=10)
                if r.status_code == 200:
                    from ..assets.processor import get_image_metadata as _img_meta
                    if not metadata["bytes_size"]:
                        metadata["bytes_size"] = len(r.content)
                    img_m = _img_meta(r.content)
                    metadata["width"] = img_m.get("width")
                    metadata["height"] = img_m.get("height")
            except Exception:
                pass

        return metadata

    @staticmethod
    def _extract_output_paths(outputs: dict) -> list[str]:
        paths: list[str] = []
        for node_outputs in outputs.values():
            if not isinstance(node_outputs, dict):
                continue
            for key in ("glb_path", "file_path", "mesh_path"):
                val = node_outputs.get(key)
                if isinstance(val, list):
                    paths.extend(val)
                elif isinstance(val, str):
                    paths.append(val)
            for img in node_outputs.get("images", []):
                if isinstance(img, dict) and "filename" in img:
                    sf = img.get("subfolder", "")
                    fn = img["filename"]
                    paths.append(f"{sf}/{fn}" if sf else fn)
            for val in node_outputs.values():
                if isinstance(val, str) and val.endswith((".glb", ".gltf")):
                    paths.append(val)
                elif isinstance(val, list):
                    for item in val:
                        if isinstance(item, str) and item.endswith((".glb", ".gltf")):
                            paths.append(item)
        return paths


def _mime_from_filename(filename: str) -> str | None:
    lower = filename.lower()
    for ext, mime in (
        (".png", "image/png"),
        (".jpg", "image/jpeg"), (".jpeg", "image/jpeg"),
        (".webp", "image/webp"),
        (".gif", "image/gif"),
        (".mp3", "audio/mpeg"),
        (".mp4", "video/mp4"),
        (".wav", "audio/wav"),
        (".flac", "audio/flac"),
    ):
        if lower.endswith(ext):
            return mime
    return None

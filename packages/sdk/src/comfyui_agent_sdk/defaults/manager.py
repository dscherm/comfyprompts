"""Per-namespace parameter defaults with precedence hierarchy.

Precedence (highest to lowest):
  1. Per-call provided values
  2. Runtime defaults (set via set_defaults)
  3. Config file defaults (~/.config/comfy-mcp/config.json)
  4. Environment variables (COMFY_MCP_DEFAULT_*_MODEL)
  5. Hardcoded defaults
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".config" / "comfy-mcp"
CONFIG_FILE = CONFIG_DIR / "config.json"

_NAMESPACES = ("image", "audio", "video", "3d")

_HARDCODED: dict[str, dict[str, Any]] = {
    "image": {
        "width": 512, "height": 512, "steps": 20, "cfg": 1.0,
        "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0,
        "negative_prompt": "", "lora_strength": 1.0, "controlnet_strength": 1.0,
    },
    "audio": {
        "steps": 50, "cfg": 5.0, "sampler_name": "euler", "scheduler": "simple",
        "denoise": 1.0, "seconds": 60, "lyrics_strength": 0.99,
        "model": "ace_step_v1_3.5b.safetensors",
    },
    "video": {
        "width": 480, "height": 272, "steps": 20, "cfg": 5.0,
        "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0,
        "negative_prompt": "blurry, low quality, distorted", "fps": 16, "frames": 33,
    },
    "3d": {
        "steps": 20, "cfg": 7.0,
        "negative_prompt": "blurry, low quality, multiple objects",
        "resolution": 256, "model": "v1-5-pruned-emaonly.ckpt",
    },
}


class DefaultsManager:
    """Manages default values with namespace-based precedence."""

    def __init__(self, comfyui_client: Any = None):
        self.comfyui_client = comfyui_client
        self._runtime: dict[str, dict[str, Any]] = {ns: {} for ns in _NAMESPACES}
        self._config = self._load_config()
        self._available_models_set: set[str] = set()
        self._invalid_models: dict[str, str] = {}

        if comfyui_client is not None:
            self.validate_all_defaults()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_default(self, namespace: str, key: str, provided_value: Any = None) -> Any:
        if provided_value is not None:
            return provided_value
        if key in self._runtime.get(namespace, {}):
            return self._runtime[namespace][key]
        if key in self._config.get(namespace, {}):
            return self._config[namespace][key]
        env = self._env_defaults()
        if key in env.get(namespace, {}):
            return env[namespace][key]
        return _HARDCODED.get(namespace, {}).get(key)

    def get_all_defaults(self) -> dict[str, dict[str, Any]]:
        env = self._env_defaults()
        result: dict[str, dict[str, Any]] = {}
        for ns in _NAMESPACES:
            merged = _HARDCODED.get(ns, {}).copy()
            merged.update(env.get(ns, {}))
            merged.update(self._config.get(ns, {}))
            merged.update(self._runtime.get(ns, {}))
            result[ns] = merged
        return result

    def set_defaults(
        self, namespace: str, defaults: dict[str, Any], validate_models: bool = True
    ) -> dict[str, Any]:
        if namespace not in _NAMESPACES:
            return {"error": f"Invalid namespace: {namespace}. Must be one of {_NAMESPACES}"}

        errors: list[str] = []
        if validate_models and "model" in defaults and self.comfyui_client:
            model = defaults["model"]
            available = self.comfyui_client.available_models
            if available and model not in available:
                errors.append(
                    f"Model '{model}' not found. Available: {available[:5]}..."
                )

        if errors:
            return {"errors": errors}

        self._runtime.setdefault(namespace, {}).update(defaults)
        return {"success": True, "updated": defaults}

    def persist_defaults(self, namespace: str, defaults: dict[str, Any]) -> dict[str, Any]:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        config: dict[str, Any] = {}
        if CONFIG_FILE.exists():
            try:
                config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        config.setdefault("defaults", {}).setdefault(namespace, {}).update(defaults)
        try:
            CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")
            self._config = self._load_config()
            return {"success": True, "persisted": defaults}
        except OSError as e:
            return {"error": f"Failed to write config: {e}"}

    def refresh_model_set(self) -> None:
        if self.comfyui_client and self.comfyui_client.available_models:
            self._available_models_set = set(self.comfyui_client.available_models)

    def is_model_valid(self, namespace: str, model: str) -> bool:
        if not model:
            return True
        if self._invalid_models.get(namespace) == model:
            return False
        return model in self._available_models_set

    @property
    def available_models_set(self) -> frozenset[str]:
        """Public read-only accessor for the set of available models."""
        return frozenset(self._available_models_set)

    def validate_default_model(self, namespace: str) -> tuple[bool, str, str]:
        """Validate the default model for a specific namespace.

        Returns:
            Tuple of (is_valid, model_name, source) where source is one of
            "runtime", "config", "env", "hardcoded", or "unknown".
        """
        model = self.get_default(namespace, "model")
        if not model:
            return (True, "", "unknown")
        source = self._get_source(namespace, "model")
        is_valid = model in self._available_models_set
        if not is_valid:
            self._invalid_models[namespace] = model
        return (is_valid, model, source)

    def validate_all_defaults(self) -> None:
        self.refresh_model_set()
        for ns in _NAMESPACES:
            model = self.get_default(ns, "model")
            if model and model not in self._available_models_set:
                src = self._get_source(ns, "model")
                logger.warning(
                    "Default model '%s' (from %s) for %s not found in ComfyUI.",
                    model, src, ns,
                )
                self._invalid_models[ns] = model

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    @staticmethod
    def _load_config() -> dict[str, dict[str, Any]]:
        defaults: dict[str, dict[str, Any]] = {ns: {} for ns in _NAMESPACES}
        if CONFIG_FILE.exists():
            try:
                cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                for ns in _NAMESPACES:
                    defaults[ns] = cfg.get("defaults", {}).get(ns, {})
            except (json.JSONDecodeError, OSError):
                pass
        return defaults

    @staticmethod
    def _env_defaults() -> dict[str, dict[str, Any]]:
        d: dict[str, dict[str, Any]] = {ns: {} for ns in _NAMESPACES}
        for ns, env_key in (
            ("image", "COMFY_MCP_DEFAULT_IMAGE_MODEL"),
            ("audio", "COMFY_MCP_DEFAULT_AUDIO_MODEL"),
            ("video", "COMFY_MCP_DEFAULT_VIDEO_MODEL"),
        ):
            v = os.getenv(env_key)
            if v:
                d[ns]["model"] = v
        return d

    def _get_source(self, namespace: str, key: str) -> str:
        if key in self._runtime.get(namespace, {}):
            return "runtime"
        if key in self._config.get(namespace, {}):
            return "config"
        if key in self._env_defaults().get(namespace, {}):
            return "env"
        if key in _HARDCODED.get(namespace, {}):
            return "hardcoded"
        return "unknown"

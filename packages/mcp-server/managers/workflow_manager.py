"""Workflow management for loading and processing ComfyUI workflows"""

import copy
import json
import logging
import random
import re
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from models.workflow import WorkflowParameter, WorkflowToolDefinition

logger = logging.getLogger("MCP_Server")

PLACEHOLDER_PREFIX = "PARAM_"
PLACEHOLDER_TYPE_HINTS = {
    "STR": str,
    "STRING": str,
    "TEXT": str,
    "INT": int,
    "FLOAT": float,
    "BOOL": bool,
}
PLACEHOLDER_DESCRIPTIONS = {
    "prompt": "Main text prompt used inside the workflow.",
    "seed": "Random seed for image generation. If not provided, a random seed will be generated.",
    "width": "Image width in pixels. Default: 512.",
    "height": "Image height in pixels. Default: 512.",
    "model": "Checkpoint model name (e.g., 'v1-5-pruned-emaonly.ckpt', 'sd_xl_base_1.0.safetensors'). Default: 'v1-5-pruned-emaonly.ckpt'.",
    "steps": "Number of sampling steps. Higher = better quality but slower. Default: 20.",
    "cfg": "Classifier-free guidance scale. Higher = more adherence to prompt. Default: 8.0.",
    "sampler_name": "Sampling method (e.g., 'euler', 'dpmpp_2m', 'ddim'). Default: 'euler'.",
    "scheduler": "Scheduler type (e.g., 'normal', 'karras', 'exponential'). Default: 'normal'.",
    "denoise": "Denoising strength (0.0-1.0). Default: 1.0.",
    "negative_prompt": "Negative prompt to avoid certain elements. Default: 'text, watermark'.",
    "tags": "Comma-separated descriptive tags for the audio model.",
    "lyrics": "Full lyric text that should drive the audio generation.",
    "seconds": "Audio duration in seconds. Default: 60 (1 minute).",
    "lyrics_strength": "How strongly lyrics influence audio generation (0.0-1.0). Default: 0.99.",
    "duration": "Video duration in seconds. Default: 5.",
    "fps": "Frames per second for video output. Default: 16.",
    "frames": "Number of frames in the video. Default: 16.",
    "motion_module": "AnimateDiff motion module name (e.g., 'mm_sd_v15_v2.ckpt', 'mm_sdxl_v10_beta.ckpt').",
    "resolution": "3D mesh geometry resolution. Higher = more detail but slower. Default: 256.",
    "image_path": "Path to the input image file for inpainting/editing.",
    "mask_path": "Path to the mask image file. White areas will be inpainted.",
    # Upscale-specific parameters
    "upscale_model": "ESRGAN upscale model name (e.g., 'RealESRGAN_x4plus.pth', '4x-UltraSharp.pth').",
    "scale_factor": "Upscale multiplier (2 or 4). Default: 4.",
    # Variations-specific parameters
    "variation_strength": "How different variations should be from original (0.0-1.0). Default: 0.7.",
    "num_variations": "Number of variations to generate (1-8). Default: 4.",
    # LoRA parameters
    "lora_name": "LoRA model name (e.g., 'Ghibli_Flux_Lora.safetensors'). Required for LoRA workflows.",
    "lora_strength": "LoRA influence strength (0.0-2.0). Default: 1.0. Higher = stronger effect.",
    # ControlNet parameters
    "control_image": "Path to the control image for ControlNet guidance.",
    "controlnet_type": "ControlNet mode: 'canny', 'tile', 'depth', 'blur', 'pose', or 'gray'.",
    "controlnet_strength": "ControlNet influence strength (0.0-1.0). Default: 1.0.",
    # TTS / Speech parameters
    "text": "Text to convert to speech. Supports [CharacterName] syntax for multi-speaker dialogue.",
    "voice_reference": "Voice reference name. Place .wav + .txt pair in voices directory. Use 'default' for engine default.",
    "rvc_model": "RVC voice model filename (.pth). Must be pre-trained on target voice.",
    "pitch_shift": "Pitch adjustment in semitones. 0 = no change, +12 = one octave up. Default: 0.",
    # Lip sync parameters
    "video_path": "Path to input video file.",
    "audio_path": "Path to input audio file.",
    "face_detect_batch": "Face detection batch size for Wav2Lip. Higher = faster but more VRAM. Default: 8.",
}
DEFAULT_OUTPUT_KEYS = ("images", "image", "gifs", "gif")
AUDIO_OUTPUT_KEYS = ("audio", "audios", "sound", "files")
VIDEO_OUTPUT_KEYS = ("videos", "video", "mp4", "mov", "webm")
MESH_OUTPUT_KEYS = ("mesh", "meshes", "3d", "obj", "glb", "files")


class WorkflowManager:
    def __init__(self, workflows_dir: Path):
        self.workflows_dir = Path(workflows_dir).resolve()
        self._tool_names: set[str] = set()
        self.tool_definitions = self._load_workflows()
        self._workflow_cache: Dict[str, Dict[str, Any]] = {}
    
    def _safe_workflow_path(self, workflow_id: str) -> Optional[Path]:
        """Resolve workflow ID to file path with path traversal protection"""
        # Normalize workflow_id (remove any path separators and dangerous characters)
        safe_id = workflow_id.replace("/", "_").replace("\\", "_").replace("..", "_")
        # Remove any remaining path-like characters
        safe_id = "".join(c for c in safe_id if c.isalnum() or c in ("_", "-"))
        if not safe_id:
            logger.warning(f"Invalid workflow_id after sanitization: {workflow_id}")
            return None
        
        workflow_path = (self.workflows_dir / f"{safe_id}.json").resolve()
        
        # Ensure the resolved path is within workflows_dir
        try:
            workflow_path.relative_to(self.workflows_dir.resolve())
        except ValueError:
            logger.warning(f"Path traversal attempt detected: {workflow_id}")
            return None
        
        return workflow_path if workflow_path.exists() else None
    
    def _load_workflow_metadata(self, workflow_path: Path) -> Dict[str, Any]:
        """Load sidecar metadata file if it exists"""
        metadata_path = workflow_path.with_suffix(".meta.json")
        if metadata_path.exists():
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load metadata for {workflow_path.name}: {e}")
        return {}
    
    def get_workflow_catalog(self) -> list[Dict[str, Any]]:
        """Get catalog of all available workflows"""
        catalog = []
        if not self.workflows_dir.exists():
            return catalog
        
        for workflow_path in sorted(self.workflows_dir.glob("*.json")):
            # Skip metadata files
            if workflow_path.name.endswith(".meta.json"):
                continue
            
            workflow_id = workflow_path.stem
            try:
                with open(workflow_path, "r", encoding="utf-8") as f:
                    workflow = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Skipping {workflow_path.name}: {e}")
                continue
            
            # Load metadata
            metadata = self._load_workflow_metadata(workflow_path)
            
            # Extract parameters
            parameters = self._extract_parameters(workflow)
            available_inputs = {
                name: {
                    "type": param.annotation.__name__,
                    "required": param.required,
                    "description": param.description
                }
                for name, param in parameters.items()
            }
            
            # Get workflow defaults from metadata or infer from workflow_id
            workflow_defaults = metadata.get("defaults", {})
            if not workflow_defaults and workflow_id in ["generate_image", "generate_song", "generate_video"]:
                # Use namespace-based defaults
                namespace = self._determine_namespace(workflow_id)
                # This will be populated by defaults_manager when needed
            
            catalog.append({
                "id": workflow_id,
                "name": metadata.get("name", workflow_id.replace("_", " ").title()),
                "description": metadata.get("description", f"Execute the '{workflow_id}' workflow."),
                "available_inputs": available_inputs,
                "defaults": workflow_defaults,
                "updated_at": metadata.get("updated_at"),
                "hash": metadata.get("hash"),  # Could compute file hash if needed
            })
        
        return catalog
    
    def load_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Load workflow by ID with caching"""
        if workflow_id in self._workflow_cache:
            return copy.deepcopy(self._workflow_cache[workflow_id])
        
        workflow_path = self._safe_workflow_path(workflow_id)
        if not workflow_path:
            return None
        
        try:
            with open(workflow_path, "r", encoding="utf-8") as f:
                workflow = json.load(f)
            self._workflow_cache[workflow_id] = workflow
            return copy.deepcopy(workflow)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load workflow {workflow_id}: {e}")
            return None
    
    def apply_workflow_overrides(self, workflow: Dict[str, Any], workflow_id: str, overrides: Dict[str, Any], defaults_manager: Optional["DefaultsManager"] = None) -> Dict[str, Any]:
        """Apply constrained overrides to workflow based on metadata"""
        from comfyui_agent_sdk.defaults import DefaultsManager
        
        workflow_path = self._safe_workflow_path(workflow_id)
        if not workflow_path:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        metadata = self._load_workflow_metadata(workflow_path)
        override_mappings = metadata.get("override_mappings", {})
        constraints = metadata.get("constraints", {})
        
        # If no metadata, try to infer from PARAM_ placeholders
        if not override_mappings:
            parameters = self._extract_parameters(workflow)
            for param_name, param in parameters.items():
                # Build mapping from parameter name to node bindings
                if param_name not in override_mappings:
                    override_mappings[param_name] = param.bindings
        
        # Determine namespace for defaults
        namespace = self._determine_namespace(workflow_id)
        
        # Apply overrides with constraints
        for param_name, value in overrides.items():
            if param_name not in override_mappings:
                logger.warning(f"Override '{param_name}' not in declared mappings for {workflow_id}, skipping")
                continue
            
            # Apply constraints if defined
            if param_name in constraints:
                constraint = constraints[param_name]
                if "enum" in constraint and value not in constraint["enum"]:
                    raise ValueError(f"Value '{value}' for '{param_name}' not in allowed enum: {constraint['enum']}")
                if "min" in constraint and value < constraint["min"]:
                    raise ValueError(f"Value '{value}' for '{param_name}' below minimum: {constraint['min']}")
                if "max" in constraint and value > constraint["max"]:
                    raise ValueError(f"Value '{value}' for '{param_name}' above maximum: {constraint['max']}")
            
            # Get parameter type from extracted parameters
            parameters = self._extract_parameters(workflow)
            if param_name in parameters:
                param = parameters[param_name]
                coerced_value = self._coerce_value(value, param.annotation)
            else:
                coerced_value = value
            
            # Apply to all bindings
            for node_id, input_name in override_mappings[param_name]:
                if node_id in workflow and "inputs" in workflow[node_id]:
                    workflow[node_id]["inputs"][input_name] = coerced_value
        
        # Apply defaults for parameters not in overrides
        parameters = self._extract_parameters(workflow)
        for param_name, param in parameters.items():
            if param_name not in overrides and not param.required:
                if defaults_manager:
                    default_value = defaults_manager.get_default(namespace, param.name, None)
                    if default_value is not None:
                        for node_id, input_name in param.bindings:
                            if node_id in workflow and "inputs" in workflow[node_id]:
                                workflow[node_id]["inputs"][input_name] = default_value
        
        return workflow

    def _load_workflows(self):
        definitions: list[WorkflowToolDefinition] = []
        if not self.workflows_dir.exists():
            logger.info("Workflow directory %s does not exist yet", self.workflows_dir)
            return definitions

        for workflow_path in sorted(self.workflows_dir.glob("*.json")):
            try:
                with open(workflow_path, "r", encoding="utf-8") as handle:
                    workflow = json.load(handle)
            except json.JSONDecodeError as exc:
                logger.error("Skipping workflow %s due to JSON error: %s", workflow_path.name, exc)
                continue

            parameters = self._extract_parameters(workflow)
            if not parameters:
                logger.info(
                    "Workflow %s has no %s placeholders; skipping auto-tool registration",
                    workflow_path.name,
                    PLACEHOLDER_PREFIX,
                )
                continue

            tool_name = self._dedupe_tool_name(self._derive_tool_name(workflow_path.stem))
            definition = WorkflowToolDefinition(
                workflow_id=workflow_path.stem,
                tool_name=tool_name,
                description=self._derive_description(workflow_path.stem),
                template=workflow,
                parameters=parameters,
                output_preferences=self._guess_output_preferences(workflow),
            )
            logger.info(
                "Prepared workflow tool '%s' from %s with params %s",
                tool_name,
                workflow_path.name,
                list(parameters.keys()),
            )
            definitions.append(definition)

        return definitions

    def render_workflow(self, definition: WorkflowToolDefinition, provided_params: Dict[str, Any], defaults_manager: Optional["DefaultsManager"] = None):
        from comfyui_agent_sdk.defaults import DefaultsManager

        workflow = copy.deepcopy(definition.template)

        # Determine namespace (image, audio, or video)
        namespace = self._determine_namespace(definition.workflow_id)

        # Assemble prompt from template if 'subject' provided but 'prompt' not
        if "subject" in provided_params and "prompt" not in provided_params:
            workflow_path = self._safe_workflow_path(definition.workflow_id)
            if workflow_path:
                metadata = self._load_workflow_metadata(workflow_path)
                template = metadata.get("prompt_template")
                if template:
                    defaults = metadata.get("defaults", {})
                    fmt_vars = {"subject": provided_params.pop("subject")}
                    for key in set(re.findall(r"\{(\w+)\}", template)) - {"subject"}:
                        fmt_vars[key] = provided_params.pop(key, None) or defaults.get(key, key)
                    provided_params["prompt"] = template.format(**fmt_vars)

        for param in definition.parameters.values():
            if param.required and param.name not in provided_params:
                raise ValueError(f"Missing required parameter '{param.name}'")
            
            # Use provided value, default, or generate (for seed)
            # Precedence: provided_params > defaults_manager > param.default (_defaults block)
            raw_value = provided_params.get(param.name)
            if raw_value is None:
                if param.name == "seed" and param.annotation is int:
                    # Special handling for seed - generate random
                    raw_value = random.randint(0, 2**32 - 1)
                    logger.debug(f"Generated random seed: {raw_value}")
                elif defaults_manager:
                    # Use defaults manager to get value with proper precedence
                    raw_value = defaults_manager.get_default(namespace, param.name, None)
                    if raw_value is not None:
                        logger.debug(f"Using default value for {param.name}: {raw_value}")
                    elif param.default is not None:
                        raw_value = param.default
                        logger.debug(f"Using workflow _defaults for {param.name}: {raw_value}")
                    else:
                        continue
                elif param.default is not None:
                    # Use workflow-embedded _defaults when no defaults_manager
                    raw_value = param.default
                    logger.debug(f"Using workflow _defaults for {param.name}: {raw_value}")
                else:
                    continue
            
            coerced_value = self._coerce_value(raw_value, param.annotation)
            for node_id, input_name in param.bindings:
                workflow[node_id]["inputs"][input_name] = coerced_value
        
        return workflow

    def _extract_parameters(self, workflow: Dict[str, Any]):
        parameters: "OrderedDict[str, WorkflowParameter]" = OrderedDict()
        # Collect _defaults from all nodes keyed by placeholder string
        workflow_defaults: Dict[str, Any] = {}
        for node_id, node in workflow.items():
            if not isinstance(node, dict):
                continue
            # Parse _defaults block if present
            node_defaults = node.get("_defaults")
            if isinstance(node_defaults, dict):
                workflow_defaults.update(node_defaults)
            inputs = node.get("inputs", {})
            if not isinstance(inputs, dict):
                continue
            for input_name, value in inputs.items():
                parsed = self._parse_placeholder(value)
                if not parsed:
                    continue
                param_name, annotation, placeholder_value = parsed
                description = PLACEHOLDER_DESCRIPTIONS.get(
                    param_name, f"Value for '{param_name}'."
                )
                parameter = parameters.get(param_name)
                if not parameter:
                    # Make seed and other optional parameters non-required
                    # Only 'prompt' should be required for generate_image
                    # Only 'tags' and 'lyrics' should be required for generate_song
                    # Only 'prompt' should be required for generate_video
                    optional_params = {
                        "seed", "width", "height", "model", "steps", "cfg",
                        "sampler_name", "scheduler", "denoise", "negative_prompt",
                        "seconds", "lyrics_strength",  # Audio-specific optional params
                        "duration", "fps", "frames", "motion_module",  # Video-specific optional params
                        "resolution",  # 3D-specific optional params
                        "lora_strength", "controlnet_strength",  # LoRA/ControlNet optional params
                        "voice_reference", "rvc_model", "pitch_shift",  # TTS/voice cloning optional params
                        "face_detect_batch",  # Lip sync optional params
                    }
                    is_required = param_name not in optional_params
                    parameter = WorkflowParameter(
                        name=param_name,
                        placeholder=placeholder_value,
                        annotation=annotation,
                        description=description,
                        required=is_required,
                    )
                    parameters[param_name] = parameter
                parameter.bindings.append((node_id, input_name))

        # Apply _defaults values to parameters (makes them non-required)
        for placeholder, default_value in workflow_defaults.items():
            parsed = self._parse_placeholder(placeholder)
            if not parsed:
                continue
            param_name, annotation, _ = parsed
            if param_name in parameters:
                param = parameters[param_name]
                param.default = default_value
                param.required = False
                logger.debug(f"Applied _defaults for {param_name}: {default_value}")

        return parameters

    def _parse_placeholder(self, value):
        if not isinstance(value, str) or not value.startswith(PLACEHOLDER_PREFIX):
            return None
        token = value[len(PLACEHOLDER_PREFIX) :]
        annotation = str
        if "_" in token:
            type_candidate, remainder = token.split("_", 1)
            type_hint = PLACEHOLDER_TYPE_HINTS.get(type_candidate.upper())
            if type_hint:
                annotation = type_hint
                token = remainder
        param_name = self._normalize_name(token)
        return param_name, annotation, value

    def _normalize_name(self, raw: str):
        cleaned = [
            (char.lower() if char.isalnum() else "_")
            for char in raw.strip()
        ]
        normalized = "".join(cleaned).strip("_")
        return normalized or "param"

    def _derive_tool_name(self, stem: str):
        return self._normalize_name(stem)

    def _dedupe_tool_name(self, base_name: str):
        name = base_name or "workflow_tool"
        if name not in self._tool_names:
            self._tool_names.add(name)
            return name
        suffix = 2
        while f"{name}_{suffix}" in self._tool_names:
            suffix += 1
        deduped = f"{name}_{suffix}"
        self._tool_names.add(deduped)
        return deduped

    def _derive_description(self, stem: str):
        readable = stem.replace("_", " ").replace("-", " ").strip()
        readable = readable if readable else stem
        return f"Execute the '{readable}' ComfyUI workflow."

    def _determine_namespace(self, workflow_id: str) -> str:
        """Determine namespace based on workflow ID."""
        if workflow_id in ("generate_song", "generate_speech", "generate_sfx", "voice_clone", "video_to_audio"):
            return "audio"
        elif workflow_id in ("generate_video", "generate_video_animatediff", "generate_video_cogvideo", "image_to_video", "lip_sync"):
            return "video"
        elif workflow_id in ("generate_3d", "generate_mesh", "image_to_3d"):
            return "3d"
        else:
            return "image"  # default fallback (includes generate_image_lora, generate_image_controlnet)
    
    def _guess_output_preferences(self, workflow: Dict[str, Any]):
        for node in workflow.values():
            if not isinstance(node, dict):
                continue
            class_type = str(node.get("class_type", "")).lower()
            if "audio" in class_type:
                return AUDIO_OUTPUT_KEYS
            if "video" in class_type or "savevideo" in class_type or "videocombine" in class_type:
                return VIDEO_OUTPUT_KEYS
            if "mesh" in class_type or "3d" in class_type or "tripo" in class_type:
                return MESH_OUTPUT_KEYS
        return DEFAULT_OUTPUT_KEYS

    def _coerce_value(self, value: Any, annotation: type):
        """Coerce a value to the specified type with proper error handling."""
        try:
            if annotation is str:
                return str(value)
            if annotation is int:
                return int(value)
            if annotation is float:
                return float(value)
            if annotation is bool:
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.strip().lower() in {"1", "true", "yes", "y"}
                return bool(value)
            return value
        except (ValueError, TypeError) as e:
            raise ValueError(f"Cannot convert {value!r} to {annotation.__name__}: {e}")

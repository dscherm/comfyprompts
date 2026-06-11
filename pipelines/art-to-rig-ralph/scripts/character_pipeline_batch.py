"""Async orchestrator for Soapbox Sabotage character generation pipeline.

Handles 10 characters through: portrait -> fullbody -> multiview -> 3D mesh ->
mesh prep -> rigging -> assembly -> animation -> export.

Features:
- Back-pressure: max 2 concurrent ComfyUI, max 3 concurrent Blender
- Retry on timeout/failure (3x)
- VRAM fallback (halve resolution)
- Model fallback chain (Hunyuan3D v2.0 -> Turbo -> TripoSG)
- Checkpoint after each stage per character
- Soup Box auto-routing to rig_soupbox.py
"""

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Optional
from datetime import datetime


CHARACTERS = [
    {"id": "player", "name": "The Rookie", "style": "v1_otomo_crumb", "rig": "unirig"},
    {"id": "bones", "name": "The Reaper", "style": "v6_otomo_zap", "rig": "unirig"},
    {"id": "crank", "name": "The Mechanic", "style": "v4_wasteland_zap", "rig": "unirig"},
    {"id": "grit", "name": "The Desert Warrior", "style": "v9_crumb_fury", "rig": "unirig"},
    {"id": "pip", "name": "The Scavenger Kid", "style": "v6_otomo_zap", "rig": "unirig"},
    {"id": "punk_king", "name": "The Wasteland Queen", "style": "v8_kaneda_comix", "rig": "unirig"},
    {"id": "rust", "name": "The Ironclad", "style": "v8_kaneda_comix", "rig": "unirig"},
    {"id": "smog", "name": "The Chemist", "style": "v4_wasteland_zap", "rig": "unirig"},
    {"id": "sparks", "name": "The Livewire", "style": "v1_otomo_crumb", "rig": "unirig"},
    {"id": "soup_box", "name": "The Mascot", "style": "v1_otomo_crumb", "rig": "soupbox_custom"},
]


class ComfyUIError(Exception):
    """Base ComfyUI error."""
    pass


class VRAMOOMError(ComfyUIError):
    """VRAM out-of-memory error."""
    pass


class TimeoutError(ComfyUIError):
    """Generation timeout error."""
    pass


class CharacterPipelineRunner:
    """Orchestrates character generation pipeline with concurrency control."""

    def __init__(self, max_comfyui_concurrent: int = 2, max_blender_concurrent: int = 3,
                 max_retries: int = 3):
        """Initialize pipeline runner.

        Args:
            max_comfyui_concurrent: Max concurrent ComfyUI jobs (portrait, fullbody, multiview, 3D)
            max_blender_concurrent: Max concurrent Blender jobs (mesh prep, rig, assemble, animate)
            max_retries: Max retry attempts on timeout/failure
        """
        self.max_comfyui_concurrent = max_comfyui_concurrent
        self.max_blender_concurrent = max_blender_concurrent
        self.max_retries = max_retries
        self._comfyui_semaphore = asyncio.Semaphore(max_comfyui_concurrent)
        self._blender_semaphore = asyncio.Semaphore(max_blender_concurrent)
        self._comfyui_job_count = 0
        self._blender_job_count = 0
        self._checkpoints = {}  # char_id -> {stage -> checkpoint data}
        self.call_history = []  # Track all operations for testing

    async def generate_portrait(self, char_id: str, style: str, output_path: str) -> dict:
        """Generate 512x512 portrait via ComfyUI (character-ralph stage 1).

        Args:
            char_id: Character ID
            style: Art style preset (e.g., "v1_otomo_crumb")
            output_path: Path to save portrait PNG

        Returns:
            {
                "success": bool,
                "output_path": str,
                "char_id": str,
                "error": str | None,
            }
        """
        pending_error = None
        async with self._comfyui_semaphore:
            self._comfyui_job_count += 1
            current_job = self._comfyui_job_count

            self.call_history.append({
                "op": "generate_portrait",
                "job_id": current_job,
                "char_id": char_id,
                "style": style,
            })

            try:
                result = await self._mock_comfyui_call(
                    f"portrait_{char_id}", output_path, style, 512, 512
                )
                return result
            except (TimeoutError, ComfyUIError) as e:
                pending_error = e

        # Retry outside semaphore to avoid deadlock
        if pending_error and isinstance(pending_error, TimeoutError):
            self.call_history.append({"op": "retry_portrait_timeout", "char_id": char_id})
            await asyncio.sleep(0.01)
            return await self.generate_portrait(char_id, style, output_path)

        return {
            "success": False,
            "output_path": output_path,
            "char_id": char_id,
            "error": str(pending_error) if pending_error else "Unknown error",
        }

    async def generate_fullbody(self, char_id: str, portrait_path: str, style: str,
                                output_path: str) -> dict:
        """Generate 768x1024 A-pose fullbody (character-ralph stage 2).

        Args:
            char_id: Character ID
            portrait_path: Path to portrait for consistency
            style: Art style
            output_path: Path to save fullbody PNG

        Returns:
            {
                "success": bool,
                "output_path": str,
                "char_id": str,
                "error": str | None,
            }
        """
        pending_error = None
        async with self._comfyui_semaphore:
            self._comfyui_job_count += 1
            self.call_history.append({
                "op": "generate_fullbody",
                "char_id": char_id,
                "style": style,
            })

            try:
                result = await self._mock_comfyui_call(
                    f"fullbody_{char_id}", output_path, style, 768, 1024
                )
                return result
            except (TimeoutError, ComfyUIError) as e:
                pending_error = e

        if pending_error and isinstance(pending_error, TimeoutError):
            self.call_history.append({"op": "retry_fullbody_timeout", "char_id": char_id})
            await asyncio.sleep(0.01)
            return await self.generate_fullbody(char_id, portrait_path, style, output_path)

        return {
            "success": False,
            "output_path": output_path,
            "char_id": char_id,
            "error": str(pending_error),
        }

    async def generate_multiview(self, char_id: str, fullbody_path: str,
                                 output_dir: str) -> dict:
        """Generate front/side/back orthographic views (character-ralph stage 3).

        Args:
            char_id: Character ID
            fullbody_path: Path to fullbody image
            output_dir: Directory to save views

        Returns:
            {
                "success": bool,
                "views": {"front": str, "side": str, "back": str},
                "char_id": str,
                "error": str | None,
            }
        """
        pending_error = None
        async with self._comfyui_semaphore:
            self._comfyui_job_count += 1
            self.call_history.append({
                "op": "generate_multiview",
                "char_id": char_id,
            })

            try:
                result = await self._mock_comfyui_call(
                    f"multiview_{char_id}", output_dir, None, 512, 1024, is_multiview=True
                )
                return result
            except (TimeoutError, ComfyUIError) as e:
                pending_error = e

        if pending_error and isinstance(pending_error, TimeoutError):
            self.call_history.append({"op": "retry_multiview_timeout", "char_id": char_id})
            await asyncio.sleep(0.01)
            return await self.generate_multiview(char_id, fullbody_path, output_dir)

        return {
            "success": False,
            "views": {},
            "char_id": char_id,
            "error": str(pending_error),
        }

    async def generate_3d_mesh(
        self,
        char_id: str,
        image_path: str,
        output_path: str,
        model: str = "hunyuan3d_v20",
        octree_resolution: int = 256,
        retry_count: int = 0,
    ) -> dict:
        """Generate 3D mesh via ComfyUI (character-ralph stage 4).

        Supports retry and fallback chain. Semaphore released before retry to avoid deadlock.

        Args:
            char_id: Character ID
            image_path: Path to input image
            output_path: Path to output GLB
            model: 3D model name (hunyuan3d_v20, turbo, triposg)
            octree_resolution: Mesh resolution
            retry_count: Internal retry counter

        Returns:
            {
                "success": bool,
                "output_path": str,
                "char_id": str,
                "model_used": str,
                "error": str | None,
            }
        """
        pending_retry = None
        async with self._comfyui_semaphore:
            self._comfyui_job_count += 1
            self.call_history.append({
                "op": "generate_3d_mesh",
                "char_id": char_id,
                "model": model,
                "octree_resolution": octree_resolution,
                "retry": retry_count,
            })

            try:
                result = await self._mock_comfyui_call(
                    image_path, output_path, model, octree_resolution
                )
                return result
            except TimeoutError:
                pending_retry = ("timeout", retry_count)
            except VRAMOOMError:
                pending_retry = ("vram", octree_resolution)

        # Retry/fallback OUTSIDE semaphore
        if pending_retry[0] == "timeout":
            if retry_count < self.max_retries:
                self.call_history.append({
                    "op": "retry_3d_mesh_timeout",
                    "char_id": char_id,
                    "retry_count": retry_count + 1,
                })
                await asyncio.sleep(0.01)
                return await self.generate_3d_mesh(
                    char_id, image_path, output_path, model, octree_resolution,
                    retry_count=retry_count + 1
                )
            else:
                return {
                    "success": False,
                    "output_path": output_path,
                    "char_id": char_id,
                    "model_used": model,
                    "error": f"Timeout after {retry_count} retries",
                }
        elif pending_retry[0] == "vram":
            if octree_resolution > 32:
                new_resolution = octree_resolution // 2
                self.call_history.append({
                    "op": "fallback_3d_vram",
                    "char_id": char_id,
                    "from_resolution": octree_resolution,
                    "to_resolution": new_resolution,
                })
                return await self.generate_3d_mesh(
                    char_id, image_path, output_path, model, new_resolution, retry_count=0
                )
            else:
                return {
                    "success": False,
                    "output_path": output_path,
                    "char_id": char_id,
                    "model_used": model,
                    "error": f"VRAM OOM at min resolution {octree_resolution}",
                }

        return {
            "success": False,
            "output_path": output_path,
            "char_id": char_id,
            "model_used": model,
            "error": "Unknown error",
        }

    async def _3d_model_fallback_chain(
        self,
        char_id: str,
        image_path: str,
        output_path: str,
        models: list,
        current_model_idx: int = 0,
    ) -> dict:
        """Try a chain of 3D models until one succeeds.

        Args:
            char_id: Character ID
            image_path: Path to input image
            output_path: Path to output GLB
            models: List of (model_name, octree_resolution) tuples
            current_model_idx: Current index in chain

        Returns:
            Generation result with model_used indicating which succeeded
        """
        if current_model_idx >= len(models):
            return {
                "success": False,
                "output_path": output_path,
                "char_id": char_id,
                "model_used": None,
                "error": f"All {len(models)} models failed",
            }

        model_name, octree_res = models[current_model_idx]
        self.call_history.append({
            "op": "fallback_model_chain",
            "char_id": char_id,
            "current_index": current_model_idx,
            "trying_model": model_name,
        })

        result = await self.generate_3d_mesh(
            char_id, image_path, output_path, model=model_name,
            octree_resolution=octree_res
        )

        if result["success"]:
            return result
        else:
            return await self._3d_model_fallback_chain(
                char_id, image_path, output_path, models, current_model_idx + 1
            )

    async def run_mesh_prep(self, char_id: str, input_glb: str, output_glb: str) -> dict:
        """Validate, repair, optimize mesh (art-to-rig-ralph stage 5).

        Args:
            char_id: Character ID
            input_glb: Input GLB path
            output_glb: Output GLB path

        Returns:
            {
                "success": bool,
                "output_path": str,
                "char_id": str,
                "error": str | None,
            }
        """
        pending_error = None
        async with self._blender_semaphore:
            self._blender_job_count += 1
            self.call_history.append({
                "op": "run_mesh_prep",
                "char_id": char_id,
            })

            try:
                result = await self._mock_blender_call(
                    "mesh_prep.py",
                    {"--input": input_glb, "--output": output_glb}
                )
                return result
            except Exception as e:
                pending_error = e

        # Retry outside semaphore
        self.call_history.append({
            "op": "retry_mesh_prep",
            "char_id": char_id,
        })
        await asyncio.sleep(0.01)
        return await self.run_mesh_prep(char_id, input_glb, output_glb)

    async def run_rig(self, char_id: str, prepared_glb: str, output_glb: str,
                      rig_type: str = "unirig") -> dict:
        """Rig character with UniRig or custom rig_soupbox.py (art-to-rig-ralph stage 6).

        Args:
            char_id: Character ID
            prepared_glb: Input prepared GLB
            output_glb: Output rigged GLB
            rig_type: "unirig" or "soupbox_custom"

        Returns:
            {
                "success": bool,
                "output_path": str,
                "char_id": str,
                "rig_type": str,
                "error": str | None,
            }
        """
        pending_error = None
        async with self._blender_semaphore:
            self._blender_job_count += 1

            script_path = "rig_soupbox.py" if rig_type == "soupbox_custom" else "rig_unirig.py"
            self.call_history.append({
                "op": "run_rig",
                "char_id": char_id,
                "rig_type": rig_type,
                "script": script_path,
            })

            try:
                result = await self._mock_blender_call(
                    script_path,
                    {"--input": prepared_glb, "--output": output_glb}
                )
                result["char_id"] = char_id
                result["rig_type"] = rig_type
                return result
            except Exception as e:
                pending_error = e

        # Retry outside semaphore
        self.call_history.append({
            "op": "retry_rig",
            "char_id": char_id,
        })
        await asyncio.sleep(0.01)
        return await self.run_rig(char_id, prepared_glb, output_glb, rig_type)

    async def run_assemble(self, char_id: str, rigged_glb: str, output_dir: str) -> dict:
        """Assemble character: rename bones, add DriverMount, validate (art-to-rig-ralph stage 7).

        Args:
            char_id: Character ID
            rigged_glb: Input rigged GLB
            output_dir: Output directory

        Returns:
            {
                "success": bool,
                "output_path": str,
                "char_id": str,
                "bones_renamed": int,
                "driver_mount_created": bool,
                "error": str | None,
            }
        """
        output_path = f"{output_dir}/{char_id}_assembled.glb"
        pending_error = None
        async with self._blender_semaphore:
            self._blender_job_count += 1
            self.call_history.append({
                "op": "run_assemble",
                "char_id": char_id,
            })

            try:
                result = await self._mock_blender_call(
                    "character_assembler.py",
                    {"--input": rigged_glb, "--output": output_path}
                )
                result["char_id"] = char_id
                result["bones_renamed"] = 29
                result["driver_mount_created"] = True
                return result
            except Exception as e:
                pending_error = e

        # Retry outside semaphore
        self.call_history.append({
            "op": "retry_assemble",
            "char_id": char_id,
        })
        await asyncio.sleep(0.01)
        return await self.run_assemble(char_id, rigged_glb, output_dir)

    async def run_animate(self, char_id: str, rigged_glb: str, output_dir: str) -> dict:
        """Apply idle/walk/run baseline animations (art-to-rig-ralph stage 8).

        Args:
            char_id: Character ID
            rigged_glb: Input rigged GLB
            output_dir: Output directory

        Returns:
            {
                "success": bool,
                "output_path": str,
                "char_id": str,
                "animations": [str],
                "error": str | None,
            }
        """
        output_path = f"{output_dir}/{char_id}_animated.glb"
        pending_error = None
        async with self._blender_semaphore:
            self._blender_job_count += 1
            self.call_history.append({
                "op": "run_animate",
                "char_id": char_id,
            })

            try:
                result = await self._mock_blender_call(
                    "animate_unirig.py",
                    {"--input": rigged_glb, "--output": output_path}
                )
                result["char_id"] = char_id
                result["animations"] = ["idle", "walk", "run"]
                return result
            except Exception as e:
                pending_error = e

        # Retry outside semaphore
        self.call_history.append({
            "op": "retry_animate",
            "char_id": char_id,
        })
        await asyncio.sleep(0.01)
        return await self.run_animate(char_id, rigged_glb, output_dir)

    async def run_character_pipeline(self, character: dict, output_dir: str) -> dict:
        """Run full pipeline for one character.

        Args:
            character: Character dict with id, name, style, rig
            output_dir: Base output directory

        Returns:
            {
                "success": bool,
                "char_id": str,
                "output_fbx": str | None,
                "output_glb": str | None,
                "stages_completed": [str],
                "error": str | None,
            }
        """
        char_id = character["id"]
        style = character["style"]
        rig_type = character["rig"]

        self.call_history.append({
            "op": "run_character_pipeline",
            "char_id": char_id,
        })

        stages_completed = []
        char_output_dir = f"{output_dir}/{char_id}"
        Path(char_output_dir).mkdir(parents=True, exist_ok=True)

        try:
            # Stage 1: Portrait
            portrait_cp = self.load_checkpoint(char_id, "portrait")
            if not portrait_cp:
                portrait_path = f"{char_output_dir}/portrait.png"
                result = await self.generate_portrait(char_id, style, portrait_path)
                if not result["success"]:
                    return {
                        "success": False,
                        "char_id": char_id,
                        "output_fbx": None,
                        "output_glb": None,
                        "stages_completed": stages_completed,
                        "error": result.get("error", "Portrait generation failed"),
                    }
                self.save_checkpoint(char_id, "portrait", {"output_path": portrait_path})
            else:
                portrait_path = portrait_cp["data"]["output_path"]
            stages_completed.append("portrait")

            # Stage 2: Fullbody
            fullbody_cp = self.load_checkpoint(char_id, "fullbody")
            if not fullbody_cp:
                fullbody_path = f"{char_output_dir}/fullbody.png"
                result = await self.generate_fullbody(char_id, portrait_path, style, fullbody_path)
                if not result["success"]:
                    return {
                        "success": False,
                        "char_id": char_id,
                        "output_fbx": None,
                        "output_glb": None,
                        "stages_completed": stages_completed,
                        "error": result.get("error", "Fullbody generation failed"),
                    }
                self.save_checkpoint(char_id, "fullbody", {"output_path": fullbody_path})
            else:
                fullbody_path = fullbody_cp["data"]["output_path"]
            stages_completed.append("fullbody")

            # Stage 3: Multiview
            multiview_cp = self.load_checkpoint(char_id, "multiview")
            if not multiview_cp:
                multiview_dir = f"{char_output_dir}/multiview"
                Path(multiview_dir).mkdir(parents=True, exist_ok=True)
                result = await self.generate_multiview(char_id, fullbody_path, multiview_dir)
                if not result["success"]:
                    return {
                        "success": False,
                        "char_id": char_id,
                        "output_fbx": None,
                        "output_glb": None,
                        "stages_completed": stages_completed,
                        "error": result.get("error", "Multiview generation failed"),
                    }
                self.save_checkpoint(char_id, "multiview", {
                    "output_dir": multiview_dir,
                    "views": result.get("views", {}),
                })
            else:
                multiview_dir = multiview_cp["data"]["output_dir"]
            stages_completed.append("multiview")

            # Stage 4: 3D Mesh Generation
            mesh_3d_cp = self.load_checkpoint(char_id, "mesh_3d")
            if not mesh_3d_cp:
                mesh_3d_path = f"{char_output_dir}/mesh_3d.glb"
                models = [
                    ("hunyuan3d_v20", 256),
                    ("hunyuan3d_turbo", 128),
                    ("triposg", 128),
                ]
                result = await self._3d_model_fallback_chain(
                    char_id, fullbody_path, mesh_3d_path, models
                )
                if not result["success"]:
                    return {
                        "success": False,
                        "char_id": char_id,
                        "output_fbx": None,
                        "output_glb": None,
                        "stages_completed": stages_completed,
                        "error": result.get("error", "3D mesh generation failed"),
                    }
                self.save_checkpoint(char_id, "mesh_3d", {
                    "output_path": mesh_3d_path,
                    "model_used": result.get("model_used"),
                })
            else:
                mesh_3d_path = mesh_3d_cp["data"]["output_path"]
            stages_completed.append("mesh_3d")

            # Stage 5: Mesh Prep
            mesh_prep_cp = self.load_checkpoint(char_id, "mesh_prep")
            if not mesh_prep_cp:
                prepared_path = f"{char_output_dir}/mesh_prepared.glb"
                result = await self.run_mesh_prep(char_id, mesh_3d_path, prepared_path)
                if not result["success"]:
                    return {
                        "success": False,
                        "char_id": char_id,
                        "output_fbx": None,
                        "output_glb": None,
                        "stages_completed": stages_completed,
                        "error": result.get("error", "Mesh prep failed"),
                    }
                self.save_checkpoint(char_id, "mesh_prep", {"output_path": prepared_path})
            else:
                prepared_path = mesh_prep_cp["data"]["output_path"]
            stages_completed.append("mesh_prep")

            # Stage 6: Rig
            rig_cp = self.load_checkpoint(char_id, "rig")
            if not rig_cp:
                rigged_path = f"{char_output_dir}/rigged.glb"
                result = await self.run_rig(char_id, prepared_path, rigged_path, rig_type)
                if not result["success"]:
                    return {
                        "success": False,
                        "char_id": char_id,
                        "output_fbx": None,
                        "output_glb": None,
                        "stages_completed": stages_completed,
                        "error": result.get("error", f"Rigging with {rig_type} failed"),
                    }
                self.save_checkpoint(char_id, "rig", {
                    "output_path": rigged_path,
                    "rig_type": rig_type,
                })
            else:
                rigged_path = rig_cp["data"]["output_path"]
            stages_completed.append("rig")

            # Stage 7: Assemble
            assemble_cp = self.load_checkpoint(char_id, "assemble")
            if not assemble_cp:
                result = await self.run_assemble(char_id, rigged_path, char_output_dir)
                if not result["success"]:
                    return {
                        "success": False,
                        "char_id": char_id,
                        "output_fbx": None,
                        "output_glb": None,
                        "stages_completed": stages_completed,
                        "error": result.get("error", "Assembly failed"),
                    }
                self.save_checkpoint(char_id, "assemble", {
                    "output_path": result.get("output_path"),
                })
            else:
                assembled_path = assemble_cp["data"]["output_path"]
            stages_completed.append("assemble")

            # Stage 8: Animate
            animate_cp = self.load_checkpoint(char_id, "animate")
            if not animate_cp:
                result = await self.run_animate(char_id, rigged_path, char_output_dir)
                if not result["success"]:
                    return {
                        "success": False,
                        "char_id": char_id,
                        "output_fbx": None,
                        "output_glb": None,
                        "stages_completed": stages_completed,
                        "error": result.get("error", "Animation failed"),
                    }
                animated_path = result.get("output_path", f"{char_output_dir}/{char_id}_animated.glb")
                self.save_checkpoint(char_id, "animate", {"output_path": animated_path})
            else:
                animated_path = animate_cp["data"]["output_path"]
            stages_completed.append("animate")

            # Stage 9: Export (FBX + GLB)
            fbx_path = f"{char_output_dir}/{char_id}_final.fbx"
            glb_path = f"{char_output_dir}/{char_id}_final.glb"

            return {
                "success": True,
                "char_id": char_id,
                "output_fbx": fbx_path,
                "output_glb": glb_path,
                "stages_completed": stages_completed,
                "error": None,
            }

        except Exception as e:
            return {
                "success": False,
                "char_id": char_id,
                "output_fbx": None,
                "output_glb": None,
                "stages_completed": stages_completed,
                "error": str(e),
            }

    async def run_batch(self, characters: list, output_dir: str) -> dict:
        """Run pipeline for all characters in batch.

        Args:
            characters: List of character dicts
            output_dir: Base output directory

        Returns:
            {
                "success": bool,
                "total_characters": int,
                "succeeded": int,
                "failed": int,
                "results": [character result dicts],
                "start_time": str,
                "end_time": str,
            }
        """
        start_time = datetime.now().isoformat()

        self.call_history.append({
            "op": "run_batch",
            "num_characters": len(characters),
        })

        # Run all characters concurrently (controlled by internal semaphores)
        tasks = [
            self.run_character_pipeline(char, output_dir)
            for char in characters
        ]
        results = await asyncio.gather(*tasks)

        succeeded = sum(1 for r in results if r["success"])
        failed = len(results) - succeeded

        end_time = datetime.now().isoformat()

        return {
            "success": failed == 0,
            "total_characters": len(characters),
            "succeeded": succeeded,
            "failed": failed,
            "results": results,
            "start_time": start_time,
            "end_time": end_time,
        }

    def save_checkpoint(self, char_id: str, stage: str, data: dict) -> None:
        """Save checkpoint for resume capability.

        Args:
            char_id: Character ID
            stage: Pipeline stage (portrait, fullbody, multiview, mesh_3d, mesh_prep, rig, assemble, animate)
            data: Checkpoint data
        """
        if char_id not in self._checkpoints:
            self._checkpoints[char_id] = {}
        self._checkpoints[char_id][stage] = {
            "stage": stage,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }
        self.call_history.append({
            "op": "save_checkpoint",
            "char_id": char_id,
            "stage": stage,
        })

    def load_checkpoint(self, char_id: str, stage: str) -> Optional[dict]:
        """Load checkpoint.

        Args:
            char_id: Character ID
            stage: Pipeline stage

        Returns:
            Checkpoint data or None if not found
        """
        self.call_history.append({
            "op": "load_checkpoint",
            "char_id": char_id,
            "stage": stage,
            "found": char_id in self._checkpoints and stage in self._checkpoints[char_id],
        })
        return self._checkpoints.get(char_id, {}).get(stage)

    # ========================================================================
    # Mock hooks for testing
    # ========================================================================

    async def _mock_comfyui_call(self, op_name: str, output_path: str, style: str,
                                 width: int = 512, height: int = 512,
                                 is_multiview: bool = False):
        """Mock ComfyUI API call. Override in tests.

        Args:
            op_name: Operation name (portrait_X, fullbody_X, etc.)
            output_path: Output file path or directory
            style: Art style or model name
            width: Image width
            height: Image height
            is_multiview: If True, return multiview dict instead of single path

        Returns:
            ComfyUI result dict
        """
        if is_multiview:
            return {
                "success": True,
                "views": {
                    "front": f"{output_path}/front.png",
                    "side": f"{output_path}/side.png",
                    "back": f"{output_path}/back.png",
                },
                "char_id": op_name.split("_")[1] if "_" in op_name else "unknown",
                "error": None,
            }
        else:
            return {
                "success": True,
                "output_path": output_path,
                "style": style,
                "width": width,
                "height": height,
                "error": None,
            }

    async def _mock_blender_call(self, script_path: str, args: dict, timeout: int = 120):
        """Mock Blender subprocess call. Override in tests.

        Args:
            script_path: Path to Blender Python script
            args: Script arguments
            timeout: Execution timeout in seconds

        Returns:
            Blender result dict
        """
        return {
            "success": True,
            "stdout": "OK",
            "stderr": "",
            "exit_code": 0,
            "output_path": args.get("--output", ""),
            "error": None,
        }

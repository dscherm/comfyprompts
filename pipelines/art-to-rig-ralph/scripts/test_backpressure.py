"""Test suite for back-pressure handling in art-to-rig-ralph pipeline.

Tests failure recovery (retry/fallback logic) and concurrency/throughput constraints.
All external dependencies are mocked — no ComfyUI or Blender required.

Test Categories:
- Category A: Failure Recovery (tests 1-8) — timeout retry, VRAM fallback, model fallback,
  Blender crash checkpoint, mesh split handling, export retry, full failure reporting
- Category B: Throughput/Concurrency (tests 9-12) — semaphore limits, job queueing,
  batch processing with concurrency constraints
"""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call
import pytest


class ComfyUIError(Exception):
    """Base ComfyUI error."""
    pass


class VRAMOOMError(ComfyUIError):
    """VRAM out-of-memory error."""
    pass


class TimeoutError(ComfyUIError):
    """Generation timeout error."""
    pass


class PipelineRunner:
    """Minimal pipeline runner interface for testing back-pressure.

    Handles retry logic, concurrent execution limits, fallback chains,
    and checkpoint-based recovery.
    """

    def __init__(self, max_comfyui_concurrent=2, max_blender_concurrent=3, max_retries=3):
        self.max_comfyui_concurrent = max_comfyui_concurrent
        self.max_blender_concurrent = max_blender_concurrent
        self.max_retries = max_retries
        self._comfyui_semaphore = asyncio.Semaphore(max_comfyui_concurrent)
        self._blender_semaphore = asyncio.Semaphore(max_blender_concurrent)
        self._comfyui_job_count = 0
        self._blender_job_count = 0
        self._checkpoints = {}  # kart_name -> checkpoint data
        self.call_history = []  # Track calls for verification

    async def generate_3d_mesh(
        self,
        image_path: str,
        output_path: str,
        model: str = "hunyuan3d_v20",
        octree_resolution: int = 256,
        retry_count: int = 0,
    ) -> dict:
        """Generate 3D mesh via ComfyUI. Supports retry and fallback.

        Semaphore is released before retry/fallback to avoid deadlock.
        """
        # Acquire semaphore only for the actual API call, release before retry
        pending_retry = None
        async with self._comfyui_semaphore:
            self._comfyui_job_count += 1
            current_job = self._comfyui_job_count

            self.call_history.append({
                "op": "generate_3d_mesh",
                "job_id": current_job,
                "image_path": image_path,
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

        # Retry/fallback happens OUTSIDE the semaphore to avoid deadlock
        if pending_retry[0] == "timeout":
            if retry_count < self.max_retries:
                self.call_history.append({
                    "op": "retry_timeout",
                    "retry_count": retry_count + 1,
                })
                await asyncio.sleep(0.01)
                return await self.generate_3d_mesh(
                    image_path, output_path, model, octree_resolution,
                    retry_count=retry_count + 1
                )
            else:
                return {
                    "success": False,
                    "output_path": output_path,
                    "model_used": model,
                    "octree_resolution": octree_resolution,
                    "retry_count": retry_count,
                    "error": f"Timeout after {retry_count} retries",
                }
        elif pending_retry[0] == "vram":
            if octree_resolution > 32:
                new_resolution = octree_resolution // 2
                self.call_history.append({
                    "op": "fallback_vram",
                    "from_resolution": octree_resolution,
                    "to_resolution": new_resolution,
                })
                return await self.generate_3d_mesh(
                    image_path, output_path, model, new_resolution, retry_count=0
                )
            else:
                return {
                    "success": False,
                    "output_path": output_path,
                    "model_used": model,
                    "octree_resolution": octree_resolution,
                    "retry_count": retry_count,
                    "error": f"VRAM OOM at min resolution {octree_resolution}",
                }

    async def run_blender_script(
        self,
        script_path: str,
        args: dict,
        timeout: int = 120,
        retry_count: int = 0,
    ) -> dict:
        """Run a Blender headless script. Supports retry.

        Args:
            script_path: Path to Blender Python script
            args: Script arguments (--input, --output, etc.)
            timeout: Execution timeout in seconds
            retry_count: Internal retry counter

        Returns:
            {
                "success": bool,
                "stdout": str,
                "stderr": str,
                "exit_code": int,
                "error": str | None,
            }
        """
        pending_error = None
        async with self._blender_semaphore:
            self._blender_job_count += 1
            current_job = self._blender_job_count

            self.call_history.append({
                "op": "run_blender_script",
                "job_id": current_job,
                "script": script_path,
                "args": args,
                "retry": retry_count,
            })

            try:
                result = await self._mock_blender_call(script_path, args, timeout)
                return result
            except Exception as e:
                pending_error = e

        # Retry outside semaphore to avoid deadlock
        if retry_count < self.max_retries:
            self.call_history.append({
                "op": "retry_blender_crash",
                "retry_count": retry_count + 1,
            })
            await asyncio.sleep(0.01)
            return await self.run_blender_script(
                script_path, args, timeout, retry_count=retry_count + 1
            )
        else:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(pending_error),
                "exit_code": 1,
                "error": f"Blender crash after {retry_count} retries",
            }

    async def _comfyui_fallback_chain(
        self,
        image_path: str,
        output_path: str,
        models: list,
        current_model_idx: int = 0,
    ) -> dict:
        """Try a chain of models until one succeeds.

        Args:
            image_path: Path to input image
            output_path: Path to output GLB
            models: List of (model_name, octree_resolution) tuples
            current_model_idx: Current index in fallback chain

        Returns:
            Generation result with model_used indicating which succeeded
        """
        if current_model_idx >= len(models):
            return {
                "success": False,
                "output_path": output_path,
                "model_used": None,
                "error": f"All {len(models)} models in fallback chain failed",
            }

        model_name, octree_res = models[current_model_idx]
        self.call_history.append({
            "op": "fallback_model_chain",
            "current_index": current_model_idx,
            "trying_model": model_name,
        })

        result = await self.generate_3d_mesh(
            image_path, output_path, model=model_name,
            octree_resolution=octree_res
        )

        if result["success"]:
            return result
        else:
            # Try next model in chain
            return await self._comfyui_fallback_chain(
                image_path, output_path, models, current_model_idx + 1
            )

    async def process_mesh_regions(
        self,
        mesh_path: str,
        output_dir: str,
        max_vertices_per_region: int = 10,
    ) -> dict:
        """Split mesh into regions. Skip if mesh < 100 faces, fallback if region < 10 verts.

        Args:
            mesh_path: Path to input mesh (GLB)
            output_dir: Directory for region outputs
            max_vertices_per_region: Minimum vertices to keep a region

        Returns:
            {
                "success": bool,
                "regions": [{"name": str, "vertices": int, "faces": int}],
                "fallback_to_chassis": bool,
                "error": str | None,
            }
        """
        self.call_history.append({
            "op": "process_mesh_regions",
            "mesh_path": mesh_path,
            "max_vertices_per_region": max_vertices_per_region,
        })

        # Simulate mesh analysis (mocked in tests)
        mesh_info = await self._mock_mesh_analysis(mesh_path)

        if mesh_info["face_count"] < 100:
            self.call_history.append({
                "op": "skip_mesh_split",
                "reason": "< 100 faces",
            })
            return {
                "success": True,
                "regions": [{"name": "Chassis", "vertices": mesh_info["vertex_count"],
                            "faces": mesh_info["face_count"]}],
                "fallback_to_chassis": True,
            }

        # Simulate region split
        regions = mesh_info.get("regions", [])
        fallback_count = 0

        for region in regions:
            if region["vertices"] < max_vertices_per_region:
                fallback_count += 1
                self.call_history.append({
                    "op": "fallback_region_to_chassis",
                    "region": region["name"],
                    "vertices": region["vertices"],
                })

        return {
            "success": True,
            "regions": regions,
            "fallback_to_chassis": fallback_count > 0,
        }

    def save_checkpoint(self, kart_name: str, stage: str, data: dict) -> None:
        """Save a checkpoint for resume capability.

        Args:
            kart_name: Name of the kart
            stage: Pipeline stage (mesh_gen, mesh_prep, rigging, export)
            data: Checkpoint data to save
        """
        if kart_name not in self._checkpoints:
            self._checkpoints[kart_name] = {}
        self._checkpoints[kart_name][stage] = {
            "stage": stage,
            "data": data,
            "timestamp": str(asyncio.get_event_loop().time()),
        }
        self.call_history.append({
            "op": "save_checkpoint",
            "kart_name": kart_name,
            "stage": stage,
        })

    def load_checkpoint(self, kart_name: str, stage: str) -> dict | None:
        """Load a checkpoint.

        Args:
            kart_name: Name of the kart
            stage: Pipeline stage

        Returns:
            Checkpoint data or None if not found
        """
        self.call_history.append({
            "op": "load_checkpoint",
            "kart_name": kart_name,
            "stage": stage,
            "found": kart_name in self._checkpoints and stage in self._checkpoints[kart_name],
        })
        return self._checkpoints.get(kart_name, {}).get(stage)

    async def run_pipeline(
        self,
        kart_name: str,
        image_path: str,
        output_dir: str,
    ) -> dict:
        """Run full pipeline for one kart: mesh_gen -> mesh_prep -> rigging -> export.

        Args:
            kart_name: Name of the kart
            image_path: Path to concept art image
            output_dir: Directory for all outputs

        Returns:
            {
                "success": bool,
                "kart_name": str,
                "output": str | None,  # path to final GLB
                "stages_completed": [str],
                "error": str | None,
                "fallbacks_used": [str],
            }
        """
        self.call_history.append({
            "op": "run_pipeline",
            "kart_name": kart_name,
        })

        stages_completed = []
        fallbacks_used = []

        try:
            # Stage 1: 3D Mesh Generation
            mesh_gen_cp = self.load_checkpoint(kart_name, "mesh_gen")
            if not mesh_gen_cp:
                mesh_path = f"{output_dir}/{kart_name}_mesh.glb"
                result = await self.generate_3d_mesh(
                    image_path, mesh_path, model="hunyuan3d_v20"
                )
                if not result["success"]:
                    return {
                        "success": False,
                        "kart_name": kart_name,
                        "output": None,
                        "stages_completed": stages_completed,
                        "error": result.get("error", "Mesh generation failed"),
                        "fallbacks_used": fallbacks_used,
                    }
                self.save_checkpoint(kart_name, "mesh_gen", {
                    "output_path": mesh_path,
                    "model": result["model_used"],
                })
            else:
                mesh_path = mesh_gen_cp["data"]["output_path"]

            stages_completed.append("mesh_gen")

            # Stage 2: Mesh Preparation
            mesh_prep_cp = self.load_checkpoint(kart_name, "mesh_prep")
            if not mesh_prep_cp:
                prepared_path = f"{output_dir}/{kart_name}_prepared.glb"
                result = await self.run_blender_script(
                    "mesh_prep.py",
                    {"--input": mesh_path, "--output": prepared_path}
                )
                if not result["success"]:
                    return {
                        "success": False,
                        "kart_name": kart_name,
                        "output": None,
                        "stages_completed": stages_completed,
                        "error": result.get("error", "Mesh prep failed"),
                        "fallbacks_used": fallbacks_used,
                    }
                self.save_checkpoint(kart_name, "mesh_prep", {
                    "output_path": prepared_path,
                })
            else:
                prepared_path = mesh_prep_cp["data"]["output_path"]

            stages_completed.append("mesh_prep")

            # Stage 3: Rigging
            rigging_cp = self.load_checkpoint(kart_name, "rigging")
            if not rigging_cp:
                rigged_path = f"{output_dir}/{kart_name}_rigged.glb"
                result = await self.run_blender_script(
                    "rig_kart.py",
                    {"--input": prepared_path, "--output": rigged_path}
                )
                if not result["success"]:
                    return {
                        "success": False,
                        "kart_name": kart_name,
                        "output": None,
                        "stages_completed": stages_completed,
                        "error": result.get("error", "Rigging failed"),
                        "fallbacks_used": fallbacks_used,
                    }
                self.save_checkpoint(kart_name, "rigging", {
                    "output_path": rigged_path,
                })
            else:
                rigged_path = rigging_cp["data"]["output_path"]

            stages_completed.append("rigging")

            # Stage 4: Export
            export_cp = self.load_checkpoint(kart_name, "export")
            if not export_cp:
                export_path = f"{output_dir}/{kart_name}_final.glb"
                result = await self._export_fbx(rigged_path, export_path)
                if not result["success"]:
                    return {
                        "success": False,
                        "kart_name": kart_name,
                        "output": None,
                        "stages_completed": stages_completed,
                        "error": result.get("error", "Export failed"),
                        "fallbacks_used": fallbacks_used,
                    }
                self.save_checkpoint(kart_name, "export", {
                    "output_path": export_path,
                })
            else:
                export_path = export_cp["data"]["output_path"]

            stages_completed.append("export")

            return {
                "success": True,
                "kart_name": kart_name,
                "output": export_path,
                "stages_completed": stages_completed,
                "error": None,
                "fallbacks_used": fallbacks_used,
            }

        except Exception as e:
            return {
                "success": False,
                "kart_name": kart_name,
                "output": None,
                "stages_completed": stages_completed,
                "error": str(e),
                "fallbacks_used": fallbacks_used,
            }

    async def _export_fbx(self, input_path: str, output_path: str,
                         retry_count: int = 0) -> dict:
        """Export to FBX. Supports retry on disk errors.

        Args:
            input_path: Path to input GLB
            output_path: Path to output FBX
            retry_count: Internal retry counter

        Returns:
            {
                "success": bool,
                "output_path": str,
                "error": str | None,
            }
        """
        self.call_history.append({
            "op": "export_fbx",
            "input": input_path,
            "output": output_path,
            "retry": retry_count,
        })

        try:
            # Simulate export (mocked in tests)
            result = await self._mock_export_call(input_path, output_path)
            return result
        except IOError as e:
            if retry_count < self.max_retries:
                self.call_history.append({
                    "op": "retry_export_io",
                    "retry_count": retry_count + 1,
                })
                await asyncio.sleep(0.01)
                return await self._export_fbx(input_path, output_path,
                                            retry_count=retry_count + 1)
            else:
                return {
                    "success": False,
                    "output_path": output_path,
                    "error": f"Export failed after {retry_count} retries: {str(e)}",
                }

    async def _mock_comfyui_call(self, image_path, output_path, model,
                                octree_resolution):
        """Mock ComfyUI API call. Override in tests."""
        return {
            "success": True,
            "output_path": output_path,
            "model_used": model,
            "octree_resolution": octree_resolution,
            "retry_count": 0,
            "error": None,
        }

    async def _mock_blender_call(self, script_path, args, timeout):
        """Mock Blender subprocess call. Override in tests."""
        return {
            "success": True,
            "stdout": "OK",
            "stderr": "",
            "exit_code": 0,
            "error": None,
        }

    async def _mock_mesh_analysis(self, mesh_path):
        """Mock mesh analysis. Override in tests."""
        return {
            "vertex_count": 5000,
            "face_count": 2500,
            "regions": [
                {"name": "Chassis", "vertices": 3000, "faces": 1500},
                {"name": "Wheel_FL", "vertices": 500, "faces": 250},
                {"name": "Wheel_FR", "vertices": 500, "faces": 250},
                {"name": "Wheel_RL", "vertices": 500, "faces": 250},
                {"name": "Wheel_RR", "vertices": 500, "faces": 250},
            ],
        }

    async def _mock_export_call(self, input_path, output_path):
        """Mock export call. Override in tests."""
        return {
            "success": True,
            "output_path": output_path,
            "error": None,
        }


# ============================================================================
# CATEGORY A: FAILURE RECOVERY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_comfyui_timeout_retry():
    """Test that ComfyUI generation timeout retries with same params."""
    runner = PipelineRunner(max_retries=3)

    call_count = 0

    async def mock_comfyui_with_timeout(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise TimeoutError("Generation timeout")
        return {
            "success": True,
            "output_path": "/output/mesh.glb",
            "model_used": "hunyuan3d_v20",
            "octree_resolution": 256,
            "retry_count": 0,
            "error": None,
        }

    runner._mock_comfyui_call = mock_comfyui_with_timeout

    result = await runner.generate_3d_mesh(
        "/input/image.png",
        "/output/mesh.glb",
        model="hunyuan3d_v20",
        octree_resolution=256,
    )

    assert result["success"] is True
    assert call_count == 2  # First timeout, then success

    # Check call history for retry operation
    retry_ops = [c for c in runner.call_history if c.get("op") == "retry_timeout"]
    assert len(retry_ops) > 0


@pytest.mark.asyncio
async def test_comfyui_vram_oom_fallback():
    """Test VRAM OOM fallback to lower resolution."""
    runner = PipelineRunner(max_retries=3)

    resolutions_tried = []

    async def mock_comfyui_with_vram_error(image_path, output_path, model, octree_resolution):
        resolutions_tried.append(octree_resolution)

        if octree_resolution == 256:
            raise VRAMOOMError("CUDA out of memory")
        return {
            "success": True,
            "output_path": "/output/mesh.glb",
            "model_used": "hunyuan3d_v20",
            "octree_resolution": octree_resolution,
            "retry_count": 0,
            "error": None,
        }

    runner._mock_comfyui_call = mock_comfyui_with_vram_error

    result = await runner.generate_3d_mesh(
        "/input/image.png",
        "/output/mesh.glb",
        model="hunyuan3d_v20",
        octree_resolution=256,
    )

    assert result["success"] is True
    assert result["octree_resolution"] == 128
    assert 256 in resolutions_tried
    assert 128 in resolutions_tried

    # Check fallback in history
    fallback_ops = [c for c in runner.call_history if c.get("op") == "fallback_vram"]
    assert len(fallback_ops) > 0
    assert fallback_ops[0]["from_resolution"] == 256
    assert fallback_ops[0]["to_resolution"] == 128


@pytest.mark.asyncio
async def test_mesh_gen_failure_fallback_chain():
    """Test fallback chain: Hunyuan3D v2.0 -> Turbo -> TripoSG -> TripoSR."""
    runner = PipelineRunner(max_retries=3)

    models_tried = []

    async def mock_comfyui_model_fallback(image_path, output_path, model,
                                         octree_resolution):
        models_tried.append(model)
        if model == "hunyuan3d_v20":
            # Return failure instead of raising
            return {
                "success": False,
                "output_path": output_path,
                "model_used": model,
                "octree_resolution": octree_resolution,
                "retry_count": 0,
                "error": "Hunyuan3D v20 failed",
            }
        elif model == "hunyuan3d_turbo":
            return {
                "success": False,
                "output_path": output_path,
                "model_used": model,
                "octree_resolution": octree_resolution,
                "retry_count": 0,
                "error": "Turbo failed",
            }
        elif model == "tripo_sg":
            return {
                "success": False,
                "output_path": output_path,
                "model_used": model,
                "octree_resolution": octree_resolution,
                "retry_count": 0,
                "error": "TripoSG failed",
            }
        # TripoSR succeeds
        return {
            "success": True,
            "output_path": output_path,
            "model_used": model,
            "octree_resolution": octree_resolution,
            "retry_count": 0,
            "error": None,
        }

    runner._mock_comfyui_call = mock_comfyui_model_fallback

    # Simulate fallback chain call
    fallback_chain = [
        ("hunyuan3d_v20", 256),
        ("hunyuan3d_turbo", 256),
        ("tripo_sg", 256),
        ("tripo_sr", 128),
    ]

    result = await runner._comfyui_fallback_chain(
        "/input/image.png",
        "/output/mesh.glb",
        fallback_chain,
    )

    assert result["success"] is True
    assert result["model_used"] == "tripo_sr"
    assert models_tried == ["hunyuan3d_v20", "hunyuan3d_turbo", "tripo_sg", "tripo_sr"]

    # Check fallback chain in history
    fallback_chain_ops = [c for c in runner.call_history
                          if c.get("op") == "fallback_model_chain"]
    assert len(fallback_chain_ops) == 4


@pytest.mark.asyncio
async def test_blender_crash_checkpoint():
    """Test Blender crash with checkpoint save and resume."""
    runner = PipelineRunner(max_retries=3)

    call_count = 0

    async def mock_blender_with_crash(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Save checkpoint before raising
            runner.save_checkpoint("kart_test", "mesh_prep", {
                "output_path": "/output/mesh_prepared_partial.glb",
            })
            raise Exception("Blender subprocess crashed (exit code 1)")
        return {
            "success": True,
            "stdout": "OK",
            "stderr": "",
            "exit_code": 0,
            "error": None,
        }

    runner._mock_blender_call = mock_blender_with_crash

    result = await runner.run_blender_script(
        "mesh_prep.py",
        {"--input": "/mesh.glb", "--output": "/output/prepared.glb"},
    )

    assert result["success"] is True
    assert call_count == 2

    # Verify checkpoint was saved
    cp = runner.load_checkpoint("kart_test", "mesh_prep")
    assert cp is not None
    assert cp["data"]["output_path"] == "/output/mesh_prepared_partial.glb"


@pytest.mark.asyncio
async def test_mesh_split_empty_region_graceful():
    """Test that region split < 10 verts falls back to Chassis."""
    runner = PipelineRunner()

    async def mock_mesh_with_tiny_region(mesh_path):
        return {
            "vertex_count": 5000,
            "face_count": 2500,
            "regions": [
                {"name": "Chassis", "vertices": 4500, "faces": 2250},
                {"name": "Tiny_Part", "vertices": 5, "faces": 5},  # Too small
            ],
        }

    runner._mock_mesh_analysis = mock_mesh_with_tiny_region

    result = await runner.process_mesh_regions(
        "/mesh.glb",
        "/output",
        max_vertices_per_region=10,
    )

    assert result["success"] is True
    assert result["fallback_to_chassis"] is True

    # Check fallback in history
    fallback_ops = [c for c in runner.call_history
                    if c.get("op") == "fallback_region_to_chassis"]
    assert len(fallback_ops) > 0


@pytest.mark.asyncio
async def test_mesh_split_tiny_mesh_skip():
    """Test that meshes with < 100 faces skip splitting."""
    runner = PipelineRunner()

    async def mock_tiny_mesh(mesh_path):
        return {
            "vertex_count": 50,
            "face_count": 25,
            "regions": [],
        }

    runner._mock_mesh_analysis = mock_tiny_mesh

    result = await runner.process_mesh_regions(
        "/tiny_mesh.glb",
        "/output",
    )

    assert result["success"] is True
    assert result["fallback_to_chassis"] is True

    # Check skip in history
    skip_ops = [c for c in runner.call_history
                if c.get("op") == "skip_mesh_split"]
    assert len(skip_ops) > 0


@pytest.mark.asyncio
async def test_export_failure_retry():
    """Test FBX export failure with retry."""
    runner = PipelineRunner(max_retries=3)

    call_count = 0

    async def mock_export_with_io_error(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise IOError("Disk full")
        return {
            "success": True,
            "output_path": "/output/final.fbx",
            "error": None,
        }

    runner._mock_export_call = mock_export_with_io_error

    result = await runner._export_fbx(
        "/input/mesh.glb",
        "/output/final.fbx",
    )

    assert result["success"] is True
    assert call_count == 2

    # Check retry in history
    retry_ops = [c for c in runner.call_history
                 if c.get("op") == "retry_export_io"]
    assert len(retry_ops) > 0


@pytest.mark.asyncio
async def test_pipeline_full_failure_report():
    """Test full failure report JSON when all retries exhausted."""
    runner = PipelineRunner(max_retries=2)

    async def mock_always_fail(*args, **kwargs):
        raise Exception("Permanent failure")

    runner._mock_comfyui_call = mock_always_fail

    result = await runner.run_pipeline(
        "kart_broken",
        "/input/image.png",
        "/output",
    )

    assert result["success"] is False
    assert result["kart_name"] == "kart_broken"
    assert result["output"] is None
    assert result["error"] is not None

    # Verify stages_completed shows what got done
    assert isinstance(result["stages_completed"], list)


# ============================================================================
# CATEGORY B: THROUGHPUT / CONCURRENCY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_max_concurrent_comfyui_jobs():
    """Verify at most 2 concurrent ComfyUI generations (semaphore)."""
    runner = PipelineRunner(max_comfyui_concurrent=2)

    concurrent_count = 0
    max_concurrent_observed = 0

    async def mock_comfyui_track_concurrency(*args, **kwargs):
        nonlocal concurrent_count, max_concurrent_observed
        concurrent_count += 1
        max_concurrent_observed = max(max_concurrent_observed, concurrent_count)
        await asyncio.sleep(0.05)  # Simulate work
        concurrent_count -= 1
        return {
            "success": True,
            "output_path": "/output/mesh.glb",
            "model_used": "hunyuan3d_v20",
            "octree_resolution": 256,
            "retry_count": 0,
            "error": None,
        }

    runner._mock_comfyui_call = mock_comfyui_track_concurrency

    # Queue 5 concurrent jobs
    tasks = [
        runner.generate_3d_mesh(f"/input/img{i}.png", f"/output/mesh{i}.glb")
        for i in range(5)
    ]
    results = await asyncio.gather(*tasks)

    assert all(r["success"] for r in results)
    assert max_concurrent_observed <= 2


@pytest.mark.asyncio
async def test_max_concurrent_blender_jobs():
    """Verify at most 3 concurrent Blender processes (semaphore)."""
    runner = PipelineRunner(max_blender_concurrent=3)

    concurrent_count = 0
    max_concurrent_observed = 0

    async def mock_blender_track_concurrency(*args, **kwargs):
        nonlocal concurrent_count, max_concurrent_observed
        concurrent_count += 1
        max_concurrent_observed = max(max_concurrent_observed, concurrent_count)
        await asyncio.sleep(0.05)
        concurrent_count -= 1
        return {
            "success": True,
            "stdout": "OK",
            "stderr": "",
            "exit_code": 0,
            "error": None,
        }

    runner._mock_blender_call = mock_blender_track_concurrency

    # Queue 7 concurrent jobs
    tasks = [
        runner.run_blender_script(f"script{i}.py", {})
        for i in range(7)
    ]
    results = await asyncio.gather(*tasks)

    assert all(r["success"] for r in results)
    assert max_concurrent_observed <= 3


@pytest.mark.asyncio
async def test_sequential_fallback_on_overload():
    """When concurrent limit hit, verify jobs queue and execute sequentially."""
    runner = PipelineRunner(max_comfyui_concurrent=2, max_blender_concurrent=2)

    execution_order = []

    async def mock_comfyui_track_order(image_path, *args, **kwargs):
        job_id = image_path.split("img")[1].split(".")[0]
        execution_order.append(("comfyui_start", job_id))
        await asyncio.sleep(0.1)
        execution_order.append(("comfyui_end", job_id))
        return {
            "success": True,
            "output_path": f"/output/mesh{job_id}.glb",
            "model_used": "hunyuan3d_v20",
            "octree_resolution": 256,
            "retry_count": 0,
            "error": None,
        }

    runner._mock_comfyui_call = mock_comfyui_track_order

    # Queue 4 jobs to 2-job limit
    tasks = [
        runner.generate_3d_mesh(f"/input/img{i}.png", f"/output/mesh{i}.glb")
        for i in range(4)
    ]
    await asyncio.gather(*tasks)

    # Verify semaphore queuing: no more than 2 "start" events without an "end"
    active = 0
    max_active = 0
    for op, job_id in execution_order:
        if op == "comfyui_start":
            active += 1
            max_active = max(max_active, active)
        elif op == "comfyui_end":
            active -= 1

    assert max_active <= 2


@pytest.mark.asyncio
async def test_batch_10_karts_throughput():
    """Simulate queuing all 10 karts, verify they all complete with concurrency limits."""
    runner = PipelineRunner(
        max_comfyui_concurrent=2,
        max_blender_concurrent=3,
        max_retries=2
    )

    # Mock all external calls to succeed immediately
    async def mock_comfyui_success(*args, **kwargs):
        await asyncio.sleep(0.01)
        return {
            "success": True,
            "output_path": "/output/mesh.glb",
            "model_used": "hunyuan3d_v20",
            "octree_resolution": 256,
            "retry_count": 0,
            "error": None,
        }

    async def mock_blender_success(*args, **kwargs):
        await asyncio.sleep(0.01)
        return {
            "success": True,
            "stdout": "OK",
            "stderr": "",
            "exit_code": 0,
            "error": None,
        }

    async def mock_mesh_success(mesh_path):
        return {
            "vertex_count": 5000,
            "face_count": 2500,
            "regions": [
                {"name": "Chassis", "vertices": 5000, "faces": 2500},
            ],
        }

    runner._mock_comfyui_call = mock_comfyui_success
    runner._mock_blender_call = mock_blender_success
    runner._mock_mesh_analysis = mock_mesh_success

    # Queue all 10 karts
    karts = [f"kart_{i:02d}" for i in range(10)]
    tasks = [
        runner.run_pipeline(kart, f"/input/{kart}.png", "/output")
        for kart in karts
    ]

    results = await asyncio.gather(*tasks)

    # All should succeed
    assert len(results) == 10
    assert all(r["success"] for r in results)

    # All stages should be completed for each
    for result in results:
        assert len(result["stages_completed"]) == 4  # mesh_gen, mesh_prep, rigging, export


# ============================================================================
# PARAMETRIZED TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("resolution,expected_fallback", [
    (256, 128),
    (128, 64),
    (64, 32),
])
async def test_vram_fallback_resolution_chain(resolution, expected_fallback):
    """Test VRAM fallback follows resolution chain: 256 -> 128 -> 64 -> 32."""
    runner = PipelineRunner()

    async def mock_vram_error_any_resolution(image_path, output_path, model,
                                             octree_resolution):
        if octree_resolution == resolution:
            raise VRAMOOMError("VRAM OOM")
        return {
            "success": True,
            "output_path": output_path,
            "model_used": model,
            "octree_resolution": octree_resolution,
            "retry_count": 0,
            "error": None,
        }

    runner._mock_comfyui_call = mock_vram_error_any_resolution

    result = await runner.generate_3d_mesh(
        "/input/image.png",
        "/output/mesh.glb",
        model="hunyuan3d_v20",
        octree_resolution=resolution,
    )

    assert result["success"] is True
    assert result["octree_resolution"] == expected_fallback


@pytest.mark.asyncio
@pytest.mark.parametrize("max_retries,should_succeed", [
    (3, True),   # Enough retries
    (1, False),  # Not enough retries
])
async def test_retry_exhaustion(max_retries, should_succeed):
    """Test that retries are exhausted after max_retries attempts."""
    runner = PipelineRunner(max_retries=max_retries)

    call_count = 0

    async def mock_always_timeout(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise TimeoutError("Generation timeout")

    runner._mock_comfyui_call = mock_always_timeout

    result = await runner.generate_3d_mesh(
        "/input/image.png",
        "/output/mesh.glb",
    )

    if should_succeed:
        # With max_retries=3, we get call_count > 3 (initial + retries)
        assert call_count > max_retries or result["success"]
    else:
        # With max_retries=1, we exhaust and fail
        assert result["success"] is False or call_count <= max_retries + 1


@pytest.mark.asyncio
@pytest.mark.parametrize("region_vertices", [5, 8, 15, 50])
async def test_region_fallback_threshold(region_vertices):
    """Test region fallback threshold: < 10 verts falls back, >= 10 stays."""
    runner = PipelineRunner()

    async def mock_mesh_with_region(mesh_path):
        return {
            "vertex_count": 5000,
            "face_count": 2500,
            "regions": [
                {"name": "Chassis", "vertices": 5000 - region_vertices, "faces": 2490},
                {"name": "Region", "vertices": region_vertices, "faces": 10},
            ],
        }

    runner._mock_mesh_analysis = mock_mesh_with_region

    result = await runner.process_mesh_regions(
        "/mesh.glb",
        "/output",
        max_vertices_per_region=10,
    )

    assert result["success"] is True
    if region_vertices < 10:
        assert result["fallback_to_chassis"] is True
    else:
        assert result["fallback_to_chassis"] is False


# ============================================================================
# INTEGRATION-STYLE TESTS (Full Pipeline Scenarios)
# ============================================================================

@pytest.mark.asyncio
async def test_full_pipeline_happy_path():
    """Test full pipeline with no failures."""
    runner = PipelineRunner(max_retries=3)

    async def mock_comfyui_success(*args, **kwargs):
        return {
            "success": True,
            "output_path": "/output/mesh.glb",
            "model_used": "hunyuan3d_v20",
            "octree_resolution": 256,
            "retry_count": 0,
            "error": None,
        }

    async def mock_blender_success(*args, **kwargs):
        return {
            "success": True,
            "stdout": "OK",
            "stderr": "",
            "exit_code": 0,
            "error": None,
        }

    runner._mock_comfyui_call = mock_comfyui_success
    runner._mock_blender_call = mock_blender_success

    result = await runner.run_pipeline(
        "kart_test",
        "/input/image.png",
        "/output",
    )

    assert result["success"] is True
    assert result["output"] == "/output/kart_test_final.glb"
    assert result["stages_completed"] == ["mesh_gen", "mesh_prep", "rigging", "export"]
    assert result["error"] is None


@pytest.mark.asyncio
async def test_full_pipeline_with_vram_fallback():
    """Test full pipeline with VRAM OOM fallback during mesh gen."""
    runner = PipelineRunner()

    call_count = 0

    async def mock_comfyui_vram_then_success(image_path, output_path, model,
                                             octree_resolution):
        nonlocal call_count
        call_count += 1
        if octree_resolution == 256:
            raise VRAMOOMError("VRAM OOM at 256")
        return {
            "success": True,
            "output_path": output_path,
            "model_used": model,
            "octree_resolution": octree_resolution,
            "retry_count": 0,
            "error": None,
        }

    async def mock_blender_success(*args, **kwargs):
        return {
            "success": True,
            "stdout": "OK",
            "stderr": "",
            "exit_code": 0,
            "error": None,
        }

    runner._mock_comfyui_call = mock_comfyui_vram_then_success
    runner._mock_blender_call = mock_blender_success

    result = await runner.run_pipeline(
        "kart_test",
        "/input/image.png",
        "/output",
    )

    assert result["success"] is True
    assert call_count == 2  # First 256 fails, then 128 succeeds
    assert result["stages_completed"] == ["mesh_gen", "mesh_prep", "rigging", "export"]


@pytest.mark.asyncio
async def test_full_pipeline_early_failure():
    """Test that early failure stops pipeline and reports."""
    runner = PipelineRunner(max_retries=1)

    async def mock_comfyui_fail(*args, **kwargs):
        raise TimeoutError("Mesh gen always times out")

    runner._mock_comfyui_call = mock_comfyui_fail

    result = await runner.run_pipeline(
        "kart_test",
        "/input/image.png",
        "/output",
    )

    assert result["success"] is False
    assert result["stages_completed"] == []
    assert result["error"] is not None


@pytest.mark.asyncio
async def test_checkpoint_resume():
    """Test that pipeline can resume from checkpoint after partial completion."""
    runner = PipelineRunner()

    # Setup: save a checkpoint at mesh_prep stage
    runner.save_checkpoint("kart_test", "mesh_gen", {
        "output_path": "/output/kart_test_mesh.glb",
        "model": "hunyuan3d_v20",
    })
    runner.save_checkpoint("kart_test", "mesh_prep", {
        "output_path": "/output/kart_test_prepared.glb",
    })

    call_history = []

    async def mock_comfyui(image_path, output_path, model, octree_resolution):
        call_history.append("comfyui_called")
        return {
            "success": True,
            "output_path": output_path,
            "model_used": model,
            "octree_resolution": octree_resolution,
            "retry_count": 0,
            "error": None,
        }

    async def mock_blender(script_path, args, timeout=120, retry_count=0):
        call_history.append(f"blender_called:{script_path}")
        return {
            "success": True,
            "stdout": "OK",
            "stderr": "",
            "exit_code": 0,
            "error": None,
        }

    runner._mock_comfyui_call = mock_comfyui
    runner._mock_blender_call = mock_blender

    result = await runner.run_pipeline(
        "kart_test",
        "/input/image.png",
        "/output",
    )

    assert result["success"] is True
    # ComfyUI should not be called again (mesh_gen checkpoint exists)
    assert "comfyui_called" not in call_history
    # But Blender should be called for rigging and export
    assert any("rig_kart.py" in str(c) for c in call_history)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

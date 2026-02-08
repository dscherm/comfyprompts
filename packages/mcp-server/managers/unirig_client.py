"""UniRig integration for AI-powered auto-rigging.

UniRig is an open-source auto-rigging framework from VAST-AI-Research that uses
autoregressive AI to predict skeleton structures joint-by-joint.

GitHub: https://github.com/VAST-AI-Research/UniRig
Paper: SIGGRAPH 2025 - "One Model to Rig Them All"

Performance:
- 215% improvement in rigging accuracy vs traditional methods
- 1-5 seconds inference time
- Supports: humans, animals, stylized characters, inorganic objects

Requirements:
- Python 3.11 (specific version required)
- CUDA GPU with 8GB+ VRAM
- PyTorch >= 2.3.1
- Various dependencies (spconv, flash-attention, etc.)

Since UniRig has specific Python version requirements, this module provides
a wrapper that can call UniRig through a conda environment or subprocess.
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("MCP_Server")


@dataclass
class UniRigConfig:
    """Configuration for UniRig."""
    unirig_path: Optional[Path] = None  # Path to UniRig installation
    conda_env: str = "UniRig"  # Conda environment name
    python_path: Optional[Path] = None  # Path to Python 3.11 for UniRig
    use_gpu: bool = True
    device: str = "cuda:0"


class UniRigClient:
    """Client for UniRig auto-rigging.

    UniRig uses a novel autoregressive approach to predict skeleton structures
    joint-by-joint, achieving state-of-the-art rigging quality.

    This client wraps UniRig's command-line interface and can optionally
    use a conda environment with the correct Python version.

    Example:
        client = UniRigClient()

        if client.is_available():
            result = client.rig_model(
                "model.glb",
                output_path="rigged.glb"
            )
    """

    def __init__(self, config: Optional[UniRigConfig] = None):
        """Initialize UniRig client.

        Args:
            config: UniRig configuration. If None, auto-detects installation.
        """
        self.config = config or UniRigConfig()
        self._unirig_path: Optional[Path] = None
        self._available: Optional[bool] = None

        # Try to find UniRig installation
        self._detect_unirig()

    def _detect_unirig(self):
        """Detect UniRig installation."""
        # Check explicit path
        if self.config.unirig_path and self.config.unirig_path.exists():
            self._unirig_path = self.config.unirig_path
            return

        # Check common locations
        possible_paths = [
            Path.home() / "UniRig",
            Path.home() / "Projects" / "UniRig",
            Path("C:/UniRig"),
            Path("C:/Projects/UniRig"),
            Path("/opt/UniRig"),
            Path.cwd() / "UniRig",
        ]

        # Also check if there's a UNIRIG_PATH environment variable
        env_path = os.getenv("UNIRIG_PATH")
        if env_path:
            possible_paths.insert(0, Path(env_path))

        for path in possible_paths:
            if path.exists() and (path / "launch").exists():
                self._unirig_path = path
                logger.info(f"Found UniRig at: {path}")
                return

        logger.info("UniRig not found. Install from: https://github.com/VAST-AI-Research/UniRig")

    @property
    def is_available(self) -> bool:
        """Check if UniRig is available."""
        if self._available is not None:
            return self._available

        if self._unirig_path is None:
            self._available = False
            return False

        # Check if the inference scripts exist
        skeleton_script = self._unirig_path / "launch" / "inference" / "generate_skeleton.sh"
        if not skeleton_script.exists():
            self._available = False
            return False

        # Check if conda environment exists (optional but recommended)
        try:
            result = subprocess.run(
                ["conda", "env", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if self.config.conda_env in result.stdout:
                logger.info(f"Found conda environment: {self.config.conda_env}")
        except Exception:
            pass  # Conda not required if Python 3.11 is available elsewhere

        self._available = True
        return True

    def _run_unirig_command(
        self,
        script_name: str,
        args: List[str],
        timeout: int = 300
    ) -> Tuple[bool, str, str]:
        """Run a UniRig command.

        Args:
            script_name: Name of the script in launch/inference/
            args: Command line arguments
            timeout: Timeout in seconds

        Returns:
            Tuple of (success, stdout, stderr)
        """
        if not self._unirig_path:
            return False, "", "UniRig not installed"

        script_path = self._unirig_path / "launch" / "inference" / script_name

        # Build command
        if os.name == "nt":
            # Windows: use bash through Git Bash or WSL
            cmd = ["bash", str(script_path)] + args
        else:
            cmd = ["bash", str(script_path)] + args

        # If using conda environment, activate it first
        if self.config.conda_env:
            if os.name == "nt":
                # Windows conda activation
                cmd = [
                    "conda", "run", "-n", self.config.conda_env,
                    "bash", str(script_path)
                ] + args
            else:
                # Unix: wrap in conda run
                cmd = [
                    "conda", "run", "-n", self.config.conda_env,
                    "bash", str(script_path)
                ] + args

        logger.info(f"Running UniRig: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self._unirig_path)
            )

            success = result.returncode == 0
            return success, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout}s"
        except Exception as e:
            return False, "", str(e)

    def rig_model(
        self,
        model_path: Path,
        output_path: Optional[Path] = None,
        output_format: str = "glb"
    ) -> Dict[str, Any]:
        """Rig a 3D model using UniRig.

        This is a three-step process:
        1. Generate skeleton structure
        2. Generate skin weights
        3. Merge skeleton and weights with original mesh

        Args:
            model_path: Path to input 3D model (GLB, FBX, OBJ, VRM)
            output_path: Path for output rigged model
            output_format: Output format (glb, fbx)

        Returns:
            Dict with result info
        """
        if not self.is_available:
            return {
                "error": "UniRig not available. Install from: https://github.com/VAST-AI-Research/UniRig",
                "available": False
            }

        model_path = Path(model_path)
        if not model_path.exists():
            return {"error": f"Model file not found: {model_path}"}

        # Create temp directory for intermediate files
        temp_dir = Path(tempfile.mkdtemp(prefix="unirig_"))

        try:
            # Step 1: Generate skeleton
            skeleton_path = temp_dir / "skeleton.fbx"
            logger.info("UniRig Step 1: Generating skeleton...")

            success, stdout, stderr = self._run_unirig_command(
                "generate_skeleton.sh",
                ["--input", str(model_path), "--output", str(skeleton_path)]
            )

            if not success:
                return {
                    "error": f"Skeleton generation failed: {stderr}",
                    "step": "skeleton"
                }

            if not skeleton_path.exists():
                return {"error": "Skeleton file not created", "step": "skeleton"}

            # Step 2: Generate skin weights
            skin_path = temp_dir / "skin.fbx"
            logger.info("UniRig Step 2: Generating skin weights...")

            success, stdout, stderr = self._run_unirig_command(
                "generate_skin.sh",
                ["--input", str(skeleton_path), "--output", str(skin_path)]
            )

            if not success:
                return {
                    "error": f"Skin weight generation failed: {stderr}",
                    "step": "skinning"
                }

            if not skin_path.exists():
                return {"error": "Skin file not created", "step": "skinning"}

            # Step 3: Merge with original mesh
            if output_path is None:
                output_path = model_path.parent / f"{model_path.stem}_unirig.{output_format}"
            else:
                output_path = Path(output_path)

            logger.info("UniRig Step 3: Merging skeleton with mesh...")

            success, stdout, stderr = self._run_unirig_command(
                "merge.sh",
                [
                    "--source", str(skin_path),
                    "--target", str(model_path),
                    "--output", str(output_path)
                ]
            )

            if not success:
                return {
                    "error": f"Merge failed: {stderr}",
                    "step": "merge"
                }

            if not output_path.exists():
                return {"error": "Output file not created", "step": "merge"}

            return {
                "success": True,
                "input_path": str(model_path),
                "output_path": str(output_path),
                "output_size": output_path.stat().st_size,
                "method": "UniRig",
                "message": "Model rigged successfully with UniRig AI"
            }

        except Exception as e:
            logger.exception(f"UniRig rigging failed: {e}")
            return {"error": str(e)}

        finally:
            # Cleanup temp directory
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass

    def get_status(self) -> Dict[str, Any]:
        """Get UniRig status and configuration.

        Returns:
            Dict with status information
        """
        return {
            "available": self.is_available,
            "unirig_path": str(self._unirig_path) if self._unirig_path else None,
            "conda_env": self.config.conda_env,
            "use_gpu": self.config.use_gpu,
            "device": self.config.device,
            "installation_url": "https://github.com/VAST-AI-Research/UniRig",
            "requirements": {
                "python": "3.11",
                "gpu_vram": "8GB+",
                "pytorch": ">=2.3.1"
            }
        }


def check_unirig_available() -> bool:
    """Quick check if UniRig is available.

    Returns:
        True if UniRig is installed and configured
    """
    client = UniRigClient()
    return client.is_available


def install_unirig_instructions() -> str:
    """Get instructions for installing UniRig.

    Returns:
        Installation instructions string
    """
    return """
UniRig Installation Instructions
================================

UniRig requires Python 3.11 and CUDA. Follow these steps:

1. Create conda environment:
   conda create -n UniRig python=3.11
   conda activate UniRig

2. Clone the repository:
   git clone https://github.com/VAST-AI-Research/UniRig
   cd UniRig

3. Install PyTorch:
   pip install torch torchvision

4. Install dependencies:
   pip install -r requirements.txt

5. Install CUDA-specific packages:
   pip install spconv-cu118  # Replace with your CUDA version
   pip install torch_scatter torch_cluster

6. Set environment variable (optional):
   export UNIRIG_PATH=/path/to/UniRig

For more details: https://github.com/VAST-AI-Research/UniRig
"""

"""External application manager for Blender and Unreal Engine integration"""

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

# Default application paths
DEFAULT_BLENDER_PATHS = [
    r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
    "/Applications/Blender.app/Contents/MacOS/Blender",
    "/usr/bin/blender",
    "/snap/bin/blender",
]

DEFAULT_UNREAL_PATHS = [
    r"C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor-Cmd.exe",
    r"C:\Program Files\Epic Games\UE_5.5\Engine\Binaries\Win64\UnrealEditor-Cmd.exe",
    r"C:\Program Files\Epic Games\UE_5.4\Engine\Binaries\Win64\UnrealEditor-Cmd.exe",
    r"C:\Program Files\Epic Games\UE_5.3\Engine\Binaries\Win64\UnrealEditor-Cmd.exe",
]

# Supported file formats
SUPPORTED_3D_FORMATS = {
    "glb": {"extensions": [".glb"], "mime_type": "model/gltf-binary"},
    "gltf": {"extensions": [".gltf"], "mime_type": "model/gltf+json"},
    "fbx": {"extensions": [".fbx"], "mime_type": "application/octet-stream"},
    "obj": {"extensions": [".obj"], "mime_type": "text/plain"},
}

SUPPORTED_IMAGE_FORMATS = {
    "png": {"extensions": [".png"], "mime_type": "image/png"},
    "jpg": {"extensions": [".jpg", ".jpeg"], "mime_type": "image/jpeg"},
    "webp": {"extensions": [".webp"], "mime_type": "image/webp"},
    "exr": {"extensions": [".exr"], "mime_type": "image/x-exr"},
    "hdr": {"extensions": [".hdr"], "mime_type": "image/vnd.radiance"},
}


@dataclass
class AppStatus:
    """Status of an external application"""
    name: str
    available: bool
    path: Optional[str]
    version: Optional[str]
    error: Optional[str] = None


class ExternalAppManager:
    """Manages integration with external applications like Blender and Unreal Engine.

    Features:
    - Auto-detect installed applications
    - Launch Blender for asset import
    - Export assets to Unreal Engine projects
    - Convert between 3D formats using Blender
    """

    def __init__(
        self,
        blender_path: Optional[str] = None,
        unreal_path: Optional[str] = None,
        scripts_dir: Optional[Path] = None
    ):
        """Initialize the external app manager.

        Args:
            blender_path: Override path to Blender executable
            unreal_path: Override path to Unreal Editor executable
            scripts_dir: Directory containing helper scripts
        """
        self.scripts_dir = scripts_dir or Path(__file__).parent.parent / "scripts"

        # Detect applications
        self._blender_path = blender_path or self._find_app(DEFAULT_BLENDER_PATHS)
        self._unreal_path = unreal_path or self._find_app(DEFAULT_UNREAL_PATHS)

        # Cache version info
        self._blender_version: Optional[str] = None
        self._unreal_version: Optional[str] = None

        if self._blender_path:
            self._blender_version = self._get_blender_version()
            logger.info(f"Blender detected: {self._blender_path} (v{self._blender_version})")
        else:
            logger.warning("Blender not found")

        if self._unreal_path:
            logger.info(f"Unreal Engine detected: {self._unreal_path}")
        else:
            logger.warning("Unreal Engine not found")

    def _find_app(self, paths: List[str]) -> Optional[str]:
        """Find first existing application from list of paths."""
        for path in paths:
            if os.path.isfile(path):
                return path
        return None

    def _get_blender_version(self) -> Optional[str]:
        """Get Blender version string."""
        if not self._blender_path:
            return None

        try:
            result = subprocess.run(
                [self._blender_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            # Parse "Blender 4.2.0" from output
            for line in result.stdout.split("\n"):
                if line.startswith("Blender"):
                    parts = line.split()
                    if len(parts) >= 2:
                        return parts[1]
            return None
        except Exception as e:
            logger.warning(f"Failed to get Blender version: {e}")
            return None

    def get_status(self) -> Dict[str, Any]:
        """Get status of all external applications.

        Returns:
            Dict with status of each application
        """
        blender_status = AppStatus(
            name="Blender",
            available=self._blender_path is not None,
            path=self._blender_path,
            version=self._blender_version
        )

        unreal_status = AppStatus(
            name="Unreal Engine",
            available=self._unreal_path is not None,
            path=self._unreal_path,
            version=self._unreal_version
        )

        return {
            "blender": {
                "available": blender_status.available,
                "path": blender_status.path,
                "version": blender_status.version
            },
            "unreal": {
                "available": unreal_status.available,
                "path": unreal_status.path,
                "version": unreal_status.version
            },
            "supported_3d_formats": list(SUPPORTED_3D_FORMATS.keys()),
            "supported_image_formats": list(SUPPORTED_IMAGE_FORMATS.keys())
        }

    def export_to_blender(
        self,
        asset_path: Path,
        action: str = "import"
    ) -> Dict[str, Any]:
        """Export an asset to Blender.

        Args:
            asset_path: Path to the asset file
            action: Action to perform - "import" opens Blender with asset loaded

        Returns:
            Dict with result info
        """
        if not self._blender_path:
            return {"error": "Blender not found. Install Blender and restart the server."}

        if not asset_path.exists():
            return {"error": f"Asset file not found: {asset_path}"}

        # Determine file type
        ext = asset_path.suffix.lower()
        is_3d = ext in [".glb", ".gltf", ".fbx", ".obj"]
        is_image = ext in [".png", ".jpg", ".jpeg", ".webp", ".exr", ".hdr"]

        if not is_3d and not is_image:
            return {"error": f"Unsupported file format: {ext}"}

        # Build import script path
        import_script = self.scripts_dir / "blender_import.py"
        if not import_script.exists():
            return {"error": f"Blender import script not found: {import_script}"}

        try:
            # Launch Blender with the import script
            cmd = [
                self._blender_path,
                "--python", str(import_script),
                "--",  # Separator for script args
                str(asset_path),
                action
            ]

            # Start Blender as detached process
            if os.name == "nt":
                # Windows: use CREATE_NEW_PROCESS_GROUP
                subprocess.Popen(
                    cmd,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                # Unix: use nohup-like behavior
                subprocess.Popen(
                    cmd,
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

            return {
                "success": True,
                "action": action,
                "asset_path": str(asset_path),
                "blender_version": self._blender_version,
                "message": f"Launched Blender with asset: {asset_path.name}"
            }

        except Exception as e:
            logger.exception(f"Failed to launch Blender: {e}")
            return {"error": f"Failed to launch Blender: {str(e)}"}

    def export_to_unreal(
        self,
        asset_path: Path,
        project_path: str,
        package_path: str = "/Game/Imports"
    ) -> Dict[str, Any]:
        """Export an asset to Unreal Engine project.

        Args:
            asset_path: Path to the asset file
            project_path: Path to the .uproject file
            package_path: Content browser path (default: /Game/Imports)

        Returns:
            Dict with result info
        """
        if not self._unreal_path:
            return {"error": "Unreal Engine not found. Install UE and restart the server."}

        if not asset_path.exists():
            return {"error": f"Asset file not found: {asset_path}"}

        project_file = Path(project_path)
        if not project_file.exists() or project_file.suffix != ".uproject":
            return {"error": f"Invalid Unreal project file: {project_path}"}

        # Validate asset format
        ext = asset_path.suffix.lower()
        supported_unreal = [".fbx", ".obj", ".png", ".jpg", ".jpeg", ".tga", ".exr", ".hdr"]
        if ext not in supported_unreal:
            return {
                "error": f"Unsupported format for Unreal import: {ext}. "
                f"Supported: {supported_unreal}. Consider using convert_3d_format first."
            }

        try:
            # Build import command
            # Unreal uses commandlets for importing
            import_dest = package_path.rstrip("/") + "/" + asset_path.stem

            cmd = [
                self._unreal_path,
                str(project_file),
                "-run=ImportAsset",
                f"-source={asset_path}",
                f"-dest={import_dest}",
                "-unattended",
                "-nopause"
            ]

            logger.info(f"Running Unreal import: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout for import
            )

            if result.returncode == 0:
                return {
                    "success": True,
                    "asset_path": str(asset_path),
                    "project_path": str(project_file),
                    "package_path": import_dest,
                    "message": f"Asset imported to {import_dest}"
                }
            else:
                return {
                    "error": f"Unreal import failed: {result.stderr[:500]}",
                    "returncode": result.returncode
                }

        except subprocess.TimeoutExpired:
            return {"error": "Unreal import timed out after 5 minutes"}
        except Exception as e:
            logger.exception(f"Failed to import to Unreal: {e}")
            return {"error": f"Failed to import to Unreal: {str(e)}"}

    def convert_3d_format(
        self,
        asset_path: Path,
        target_format: str,
        output_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Convert a 3D asset to a different format using Blender.

        Args:
            asset_path: Path to the source 3D file
            target_format: Target format (glb, gltf, fbx, obj)
            output_dir: Optional output directory. Defaults to same as source.

        Returns:
            Dict with converted file info
        """
        if not self._blender_path:
            return {"error": "Blender not found. Blender is required for format conversion."}

        if not asset_path.exists():
            return {"error": f"Source file not found: {asset_path}"}

        target_format = target_format.lower().lstrip(".")
        if target_format not in SUPPORTED_3D_FORMATS:
            return {
                "error": f"Unsupported target format: {target_format}. "
                f"Supported: {list(SUPPORTED_3D_FORMATS.keys())}"
            }

        # Validate source format
        source_ext = asset_path.suffix.lower()
        if source_ext not in [".glb", ".gltf", ".fbx", ".obj"]:
            return {"error": f"Cannot convert from {source_ext}. Supported: .glb, .gltf, .fbx, .obj"}

        # Determine output path
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        else:
            output_dir = asset_path.parent

        output_path = output_dir / f"{asset_path.stem}.{target_format}"

        # Build conversion script path
        convert_script = self.scripts_dir / "blender_convert.py"
        if not convert_script.exists():
            return {"error": f"Blender conversion script not found: {convert_script}"}

        try:
            cmd = [
                self._blender_path,
                "--background",  # Run without UI
                "--python", str(convert_script),
                "--",
                str(asset_path),
                str(output_path),
                target_format
            ]

            logger.info(f"Running Blender conversion: {asset_path} -> {output_path}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )

            if result.returncode != 0:
                return {
                    "error": f"Conversion failed: {result.stderr[:500]}",
                    "returncode": result.returncode
                }

            if not output_path.exists():
                return {"error": "Conversion completed but output file not found"}

            return {
                "success": True,
                "source_path": str(asset_path),
                "source_format": source_ext.lstrip("."),
                "output_path": str(output_path),
                "target_format": target_format,
                "bytes_size": output_path.stat().st_size,
                "message": f"Converted {asset_path.name} to {target_format}"
            }

        except subprocess.TimeoutExpired:
            return {"error": "Conversion timed out after 2 minutes"}
        except Exception as e:
            logger.exception(f"Failed to convert: {e}")
            return {"error": f"Failed to convert: {str(e)}"}

    def get_asset_format(self, asset_path: Path) -> Optional[str]:
        """Determine format of an asset file.

        Returns:
            Format string (e.g., 'glb', 'png') or None if unknown
        """
        ext = asset_path.suffix.lower().lstrip(".")

        # Check 3D formats
        for fmt, info in SUPPORTED_3D_FORMATS.items():
            if f".{ext}" in info["extensions"]:
                return fmt

        # Check image formats
        for fmt, info in SUPPORTED_IMAGE_FORMATS.items():
            if f".{ext}" in info["extensions"]:
                return fmt

        return None

    def auto_rig_model(
        self,
        asset_path: Path,
        rig_type: str = "humanoid",
        auto_weights: bool = True,
        generate_ik: bool = True,
        output_path: Optional[Path] = None,
        custom_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Auto-rig a 3D model with a skeleton for animation.

        Creates an armature/skeleton and automatically assigns vertex weights
        so the model can be animated.

        Args:
            asset_path: Path to the 3D model file (GLB, GLTF, FBX, OBJ)
            rig_type: Type of rig to create:
                - "humanoid": Full humanoid rig (uses Rigify if available)
                - "biped_simple": Simplified two-legged rig
                - "quadruped": Four-legged animal rig
                - "simple": Basic spine chain
                - "custom": Custom bones from options
            auto_weights: Automatically paint vertex weights
            generate_ik: Add IK constraints for easier posing
            output_path: Optional path to save the rigged .blend file
            custom_options: Additional options for rigging:
                - num_bones: Number of bones for simple rig
                - bones: List of bone definitions for custom rig
                - symmetrize: Make rig symmetrical

        Returns:
            Dict with result info including armature details
        """
        if not self._blender_path:
            return {"error": "Blender not found. Install Blender and restart the server."}

        if not asset_path.exists():
            return {"error": f"Asset file not found: {asset_path}"}

        # Validate file format
        ext = asset_path.suffix.lower()
        if ext not in [".glb", ".gltf", ".fbx", ".obj"]:
            return {"error": f"Unsupported 3D format for rigging: {ext}. Supported: .glb, .gltf, .fbx, .obj"}

        # Validate rig type
        valid_rig_types = ["humanoid", "biped_simple", "quadruped", "simple", "custom"]
        if rig_type not in valid_rig_types:
            return {"error": f"Invalid rig type: {rig_type}. Valid types: {valid_rig_types}"}

        # Build options JSON
        options = {
            "auto_weights": auto_weights,
            "generate_ik": generate_ik,
            **(custom_options or {})
        }

        if output_path:
            options["output_path"] = str(output_path)

        # Find autorig script
        autorig_script = self.scripts_dir / "blender_autorig.py"
        if not autorig_script.exists():
            return {"error": f"Auto-rig script not found: {autorig_script}"}

        try:
            cmd = [
                self._blender_path,
                "--python", str(autorig_script),
                "--",
                str(asset_path),
                rig_type,
                json.dumps(options)
            ]

            # If output_path specified, run in background mode
            if output_path:
                cmd.insert(1, "--background")

                logger.info(f"Running Blender auto-rig (background): {asset_path} -> {output_path}")

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=180  # 3 minute timeout for rigging
                )

                if result.returncode != 0:
                    return {
                        "error": f"Auto-rig failed: {result.stderr[:500]}",
                        "stdout": result.stdout[:500],
                        "returncode": result.returncode
                    }

                if output_path and not Path(output_path).exists():
                    return {"error": "Rigging completed but output file not found"}

                return {
                    "success": True,
                    "asset_path": str(asset_path),
                    "rig_type": rig_type,
                    "output_path": str(output_path) if output_path else None,
                    "auto_weights": auto_weights,
                    "generate_ik": generate_ik,
                    "message": f"Model rigged with {rig_type} skeleton",
                    "blender_output": result.stdout[-1000:] if result.stdout else None
                }

            else:
                # Launch Blender with UI for interactive editing
                logger.info(f"Launching Blender auto-rig (interactive): {asset_path}")

                if os.name == "nt":
                    subprocess.Popen(
                        cmd,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                else:
                    subprocess.Popen(
                        cmd,
                        start_new_session=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )

                return {
                    "success": True,
                    "asset_path": str(asset_path),
                    "rig_type": rig_type,
                    "auto_weights": auto_weights,
                    "generate_ik": generate_ik,
                    "blender_version": self._blender_version,
                    "message": f"Launched Blender with {rig_type} rig for: {asset_path.name}"
                }

        except subprocess.TimeoutExpired:
            return {"error": "Auto-rig timed out after 3 minutes"}
        except Exception as e:
            logger.exception(f"Failed to auto-rig model: {e}")
            return {"error": f"Failed to auto-rig: {str(e)}"}

    def animate_model(
        self,
        blend_path: Path,
        animation_type: str = "idle",
        duration: float = 2.0,
        fps: int = 30,
        loop: bool = True,
        intensity: float = 1.0,
        output_path: Optional[Path] = None,
        output_format: str = "glb",
        render_video: bool = False,
        video_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Generate procedural animations for a rigged model.

        Creates animations like walk cycles, idle breathing, jumps, and gestures.
        The model must already be rigged (use auto_rig_model first).

        Args:
            blend_path: Path to a rigged .blend file
            animation_type: Type of animation to generate:
                - "walk": Walking cycle
                - "run": Running cycle
                - "idle": Breathing/idle animation
                - "wave": Waving gesture
                - "jump": Jump animation
                - "nod": Head nodding
                - "look_around": Looking left and right
            duration: Animation duration in seconds
            fps: Frames per second
            loop: Make animation loop-friendly
            intensity: Animation intensity multiplier (0.5 = subtle, 1.0 = normal, 1.5 = exaggerated)
            output_path: Path to export animated model (GLB, FBX, or BLEND)
            output_format: Export format (glb, fbx, blend)
            render_video: Render animation to MP4 video
            video_path: Path for rendered video (if render_video=True)

        Returns:
            Dict with animation info and output paths
        """
        if not self._blender_path:
            return {"error": "Blender not found. Install Blender and restart the server."}

        blend_path = Path(blend_path)
        if not blend_path.exists():
            return {"error": f"Blend file not found: {blend_path}"}

        if blend_path.suffix.lower() != ".blend":
            return {"error": f"Expected .blend file, got: {blend_path.suffix}"}

        # Validate animation type
        valid_animations = ["walk", "run", "idle", "wave", "jump", "nod", "look_around"]
        if animation_type not in valid_animations:
            return {"error": f"Invalid animation type: {animation_type}. Valid types: {valid_animations}"}

        # Build options JSON
        options = {
            "duration": duration,
            "fps": fps,
            "loop": loop,
            "intensity": intensity,
            "output_format": output_format,
            "render_video": render_video,
        }

        if output_path:
            options["output_path"] = str(output_path)

        if video_path:
            options["video_path"] = str(video_path)

        # Find animate script
        animate_script = self.scripts_dir / "blender_animate.py"
        if not animate_script.exists():
            return {"error": f"Animation script not found: {animate_script}"}

        try:
            cmd = [
                self._blender_path,
                "--background",
                str(blend_path),
                "--python", str(animate_script),
                "--",
                animation_type,
                json.dumps(options)
            ]

            logger.info(f"Running Blender animation: {animation_type} on {blend_path}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout (video rendering can take time)
            )

            if result.returncode != 0:
                return {
                    "error": f"Animation failed: {result.stderr[:500]}",
                    "stdout": result.stdout[:500],
                    "returncode": result.returncode
                }

            # Build response
            response = {
                "success": True,
                "blend_path": str(blend_path),
                "animation_type": animation_type,
                "duration": duration,
                "fps": fps,
                "total_frames": int(duration * fps),
                "loop": loop,
                "intensity": intensity,
                "message": f"Generated {animation_type} animation ({duration}s at {fps}fps)"
            }

            if output_path:
                output_path = Path(output_path)
                if output_path.exists():
                    response["output_path"] = str(output_path)
                    response["output_size"] = output_path.stat().st_size

            if render_video and video_path:
                video_path = Path(video_path)
                if video_path.exists():
                    response["video_path"] = str(video_path)
                    response["video_size"] = video_path.stat().st_size

            return response

        except subprocess.TimeoutExpired:
            return {"error": "Animation timed out after 5 minutes"}
        except Exception as e:
            logger.exception(f"Failed to animate model: {e}")
            return {"error": f"Failed to animate: {str(e)}"}

    def list_animation_types(self) -> Dict[str, Any]:
        """List available animation types with descriptions.

        Returns:
            Dict with animation type information
        """
        return {
            "animation_types": [
                {
                    "type": "walk",
                    "name": "Walk Cycle",
                    "description": "Natural walking animation with arm swing and hip sway",
                    "recommended_duration": 1.0,
                    "loopable": True
                },
                {
                    "type": "run",
                    "name": "Run Cycle",
                    "description": "Running animation with arm pumping and body lean",
                    "recommended_duration": 0.6,
                    "loopable": True
                },
                {
                    "type": "idle",
                    "name": "Idle/Breathing",
                    "description": "Subtle breathing and weight shift animation",
                    "recommended_duration": 3.0,
                    "loopable": True
                },
                {
                    "type": "wave",
                    "name": "Wave Gesture",
                    "description": "Friendly waving animation with raised arm",
                    "recommended_duration": 2.0,
                    "loopable": False
                },
                {
                    "type": "jump",
                    "name": "Jump",
                    "description": "Complete jump animation: crouch, launch, air, land",
                    "recommended_duration": 1.0,
                    "loopable": False
                },
                {
                    "type": "nod",
                    "name": "Head Nod",
                    "description": "Nodding yes animation",
                    "recommended_duration": 1.5,
                    "loopable": False
                },
                {
                    "type": "look_around",
                    "name": "Look Around",
                    "description": "Looking left and right with head turns",
                    "recommended_duration": 3.0,
                    "loopable": True
                }
            ],
            "tips": [
                "Use intensity < 1.0 for subtle animations",
                "Use intensity > 1.0 for exaggerated/cartoon style",
                "Walk/run cycles work best with loopable duration",
                "Export as GLB for web/game engines, FBX for Unity/Unreal"
            ]
        }

    def import_mocap(
        self,
        blend_path: Path,
        mocap_path: Path,
        scale: float = 1.0,
        start_frame: int = 1,
        use_fps_scale: bool = True,
        output_path: Optional[Path] = None,
        output_format: str = "glb"
    ) -> Dict[str, Any]:
        """Import motion capture data (BVH/FBX) and apply to a rigged model.

        Imports BVH or FBX motion capture files and retargets the animation
        to the character's rig. Supports Mixamo and CMU mocap formats.

        Args:
            blend_path: Path to a rigged .blend file
            mocap_path: Path to the mocap file (BVH or FBX with animation)
            scale: Scale factor for the mocap data
            start_frame: Start frame for the animation
            use_fps_scale: Scale animation to match scene FPS
            output_path: Path to export animated model (GLB, FBX, or BLEND)
            output_format: Export format (glb, fbx, blend)

        Returns:
            Dict with import result and output paths
        """
        if not self._blender_path:
            return {"error": "Blender not found. Install Blender and restart the server."}

        blend_path = Path(blend_path)
        mocap_path = Path(mocap_path)

        if not blend_path.exists():
            return {"error": f"Blend file not found: {blend_path}"}

        if blend_path.suffix.lower() != ".blend":
            return {"error": f"Expected .blend file, got: {blend_path.suffix}"}

        if not mocap_path.exists():
            return {"error": f"Mocap file not found: {mocap_path}"}

        # Validate mocap format
        mocap_ext = mocap_path.suffix.lower()
        if mocap_ext not in [".bvh", ".fbx"]:
            return {"error": f"Unsupported mocap format: {mocap_ext}. Supported: .bvh, .fbx"}

        # Build options JSON
        options = {
            "scale": scale,
            "start_frame": start_frame,
            "use_fps_scale": use_fps_scale,
            "output_format": output_format,
        }

        if output_path:
            options["output_path"] = str(output_path)

        # Find mocap import script
        mocap_script = self.scripts_dir / "blender_mocap_import.py"
        if not mocap_script.exists():
            return {"error": f"Mocap import script not found: {mocap_script}"}

        try:
            cmd = [
                self._blender_path,
                "--background",
                str(blend_path),
                "--python", str(mocap_script),
                "--",
                str(mocap_path),
                json.dumps(options)
            ]

            logger.info(f"Running Blender mocap import: {mocap_path} -> {blend_path}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode != 0:
                return {
                    "error": f"Mocap import failed: {result.stderr[:500]}",
                    "stdout": result.stdout[:500],
                    "returncode": result.returncode
                }

            # Build response
            response = {
                "success": True,
                "blend_path": str(blend_path),
                "mocap_path": str(mocap_path),
                "mocap_format": mocap_ext.lstrip(".").upper(),
                "scale": scale,
                "start_frame": start_frame,
                "message": f"Imported {mocap_path.name} motion capture"
            }

            if output_path:
                output_path = Path(output_path)
                if output_path.exists():
                    response["output_path"] = str(output_path)
                    response["output_size"] = output_path.stat().st_size

            return response

        except subprocess.TimeoutExpired:
            return {"error": "Mocap import timed out after 5 minutes"}
        except Exception as e:
            logger.exception(f"Failed to import mocap: {e}")
            return {"error": f"Failed to import mocap: {str(e)}"}

    def smart_rig_model(
        self,
        asset_path: Path,
        backend: str = "auto",
        rig_type: str = "humanoid",
        output_path: Optional[Path] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Smart auto-rigging with multiple backend options.

        Supports multiple rigging backends with automatic fallback:
        - UniRig: AI-powered rigging (best quality, requires installation)
        - Tripo3D: Cloud-based AI rigging (requires API key)
        - Rigify: Blender's built-in rigging (always available)

        Args:
            asset_path: Path to 3D model file (GLB, FBX, OBJ)
            backend: Rigging backend to use:
                - "auto": Try UniRig -> Tripo3D -> Rigify
                - "unirig": Use UniRig AI
                - "tripo": Use Tripo3D cloud API
                - "rigify": Use Blender Rigify
            rig_type: Type of rig (humanoid, quadruped, simple)
            output_path: Output path for rigged model
            **kwargs: Additional backend-specific options

        Returns:
            Dict with result info including backend used
        """
        asset_path = Path(asset_path)
        if not asset_path.exists():
            return {"error": f"Asset file not found: {asset_path}"}

        backends_to_try = []

        if backend == "auto":
            # Try in order of quality: UniRig -> Tripo3D -> Rigify
            backends_to_try = ["unirig", "tripo", "rigify"]
        else:
            backends_to_try = [backend]

        last_error = None

        for be in backends_to_try:
            logger.info(f"Attempting rigging with backend: {be}")

            if be == "unirig":
                result = self._rig_with_unirig(asset_path, output_path, **kwargs)
            elif be == "tripo":
                result = self._rig_with_tripo(asset_path, output_path, **kwargs)
            elif be == "rigify":
                result = self.auto_rig_model(
                    asset_path=asset_path,
                    rig_type=rig_type,
                    output_path=output_path,
                    **kwargs
                )
            else:
                result = {"error": f"Unknown backend: {be}"}

            if "error" not in result:
                result["backend_used"] = be
                return result

            last_error = result.get("error", "Unknown error")
            logger.warning(f"Backend {be} failed: {last_error}")

        return {
            "error": f"All rigging backends failed. Last error: {last_error}",
            "tried_backends": backends_to_try
        }

    def _rig_with_unirig(
        self,
        asset_path: Path,
        output_path: Optional[Path] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Rig model using UniRig AI.

        Args:
            asset_path: Path to 3D model
            output_path: Output path

        Returns:
            Result dict
        """
        try:
            from managers.unirig_client import UniRigClient

            client = UniRigClient()
            if not client.is_available:
                return {"error": "UniRig not installed or configured"}

            return client.rig_model(asset_path, output_path)

        except ImportError:
            return {"error": "UniRig client module not available"}
        except Exception as e:
            return {"error": f"UniRig failed: {str(e)}"}

    def _rig_with_tripo(
        self,
        asset_path: Path,
        output_path: Optional[Path] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Rig model using Tripo3D cloud API.

        Args:
            asset_path: Path to 3D model
            output_path: Output path

        Returns:
            Result dict
        """
        try:
            from managers.tripo_client import TripoClientSync

            client = TripoClientSync()
            if not client.is_configured:
                return {"error": "Tripo3D API key not configured. Set TRIPO_API_KEY environment variable."}

            result = client.rig_model(asset_path)

            # Download the rigged model if successful
            if result.get("success") and result.get("rigged_model_url"):
                import httpx

                output_path = output_path or asset_path.parent / f"{asset_path.stem}_tripo_rigged.glb"

                response = httpx.get(result["rigged_model_url"], timeout=120)
                response.raise_for_status()

                with open(output_path, "wb") as f:
                    f.write(response.content)

                result["output_path"] = str(output_path)
                result["output_size"] = output_path.stat().st_size

            return result

        except ImportError:
            return {"error": "Tripo3D client module not available"}
        except Exception as e:
            return {"error": f"Tripo3D failed: {str(e)}"}

    def get_rigging_backends(self) -> Dict[str, Any]:
        """Get status of available rigging backends.

        Returns:
            Dict with backend availability info
        """
        backends = {
            "rigify": {
                "name": "Rigify",
                "available": self._blender_path is not None,
                "type": "local",
                "description": "Blender's built-in rigging system"
            }
        }

        # Check UniRig
        try:
            from managers.unirig_client import UniRigClient
            client = UniRigClient()
            backends["unirig"] = {
                "name": "UniRig AI",
                "available": client.is_available,
                "type": "local",
                "description": "AI-powered rigging from VAST-AI (best quality)",
                "status": client.get_status()
            }
        except ImportError:
            backends["unirig"] = {
                "name": "UniRig AI",
                "available": False,
                "type": "local",
                "description": "AI-powered rigging (module not installed)"
            }

        # Check Tripo3D
        try:
            from managers.tripo_client import TripoClientSync
            client = TripoClientSync()
            backends["tripo"] = {
                "name": "Tripo3D Cloud",
                "available": client.is_configured,
                "type": "cloud",
                "description": "Cloud-based AI rigging (requires API key)"
            }
        except ImportError:
            backends["tripo"] = {
                "name": "Tripo3D Cloud",
                "available": False,
                "type": "cloud",
                "description": "Cloud-based AI rigging (module not installed)"
            }

        return {
            "backends": backends,
            "recommended": self._get_recommended_backend(backends)
        }

    def _get_recommended_backend(self, backends: Dict) -> str:
        """Get recommended backend based on availability."""
        # Prefer UniRig for best quality
        if backends.get("unirig", {}).get("available"):
            return "unirig"
        # Fall back to Tripo3D if configured
        if backends.get("tripo", {}).get("available"):
            return "tripo"
        # Default to Rigify
        return "rigify"

"""External application integration tools for Blender and Unreal Engine"""

import logging
from pathlib import Path
from typing import Optional

import requests
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("MCP_Server")


def register_external_tools(
    mcp: FastMCP,
    external_app_manager,
    asset_registry
):
    """Register external application integration tools with the MCP server"""

    @mcp.tool()
    def get_external_app_status() -> dict:
        """Get status of external applications (Blender, Unreal Engine).

        Returns information about detected external applications,
        their versions, and supported file formats.

        Returns:
            Dict with:
            - blender: Blender availability, path, and version
            - unreal: Unreal Engine availability, path, and version
            - supported_3d_formats: List of supported 3D formats (glb, gltf, fbx, obj)
            - supported_image_formats: List of supported image formats

        Examples:
            get_external_app_status()
            # Returns: {"blender": {"available": true, "version": "4.2"}, ...}
        """
        return external_app_manager.get_status()

    @mcp.tool()
    def export_to_blender(
        asset_id: str,
        action: str = "import"
    ) -> dict:
        """Export an asset to Blender.

        Opens Blender with the specified asset loaded. Supports 3D models
        (glTF, FBX, OBJ) and images (PNG, JPG, EXR, HDR).

        **Requirements:**
        - Blender must be installed (auto-detected from common locations)
        - For 3D: Asset must be a generate_3d or image_to_3d output, or a converted 3D file
        - For images: Any image asset can be imported as a textured plane

        Args:
            asset_id: ID of the asset to export
            action: Action to perform. Currently only "import" is supported.

        Returns:
            Dict with:
            - success: True if Blender was launched
            - blender_version: Detected Blender version
            - message: Status message

        Examples:
            # Export a 3D model to Blender
            generate_3d(prompt="a wooden chair") -> export_to_blender(asset_id=...)

            # Export an image to Blender as a plane
            generate_image(prompt="a texture") -> export_to_blender(asset_id=...)
        """
        try:
            # Get the asset
            asset = asset_registry.get_asset(asset_id)
            if not asset:
                return {
                    "error": f"Asset {asset_id} not found or expired."
                }

            # Determine asset path
            # For ComfyUI assets, we need to download or locate the file
            asset_url = asset.asset_url or asset.get_asset_url(asset_registry.comfyui_base_url)

            # Download to temp file for Blender import
            import tempfile
            import os

            ext = Path(asset.filename).suffix.lower() or ".png"
            temp_dir = Path(tempfile.gettempdir()) / "comfyui_mcp_exports"
            temp_dir.mkdir(exist_ok=True)

            temp_path = temp_dir / f"{asset_id[:8]}{ext}"

            # Download the asset
            try:
                response = requests.get(asset_url, timeout=60)
                response.raise_for_status()
                with open(temp_path, "wb") as f:
                    f.write(response.content)
            except requests.RequestException as e:
                return {"error": f"Failed to download asset: {e}"}

            # Export to Blender
            result = external_app_manager.export_to_blender(temp_path, action)

            if "error" not in result:
                result["asset_id"] = asset_id
                result["original_filename"] = asset.filename

            return result

        except Exception as e:
            logger.exception(f"Failed to export to Blender: {e}")
            return {"error": f"Failed to export to Blender: {str(e)}"}

    @mcp.tool()
    def export_to_unreal(
        asset_id: str,
        project_path: str,
        package_path: str = "/Game/Imports"
    ) -> dict:
        """Export an asset to an Unreal Engine project.

        Imports the asset directly into an Unreal Engine project's content browser.

        **Requirements:**
        - Unreal Engine must be installed
        - Asset must be in a format Unreal supports (FBX recommended for 3D, PNG/JPG for images)
        - Use convert_3d_format first to convert glTF to FBX if needed

        **Note:** glTF/GLB files are not directly supported by Unreal's import commandlet.
        Use convert_3d_format(asset_id, "fbx") first to convert to FBX.

        Args:
            asset_id: ID of the asset to export
            project_path: Path to the .uproject file
            package_path: Content browser destination (default: "/Game/Imports")

        Returns:
            Dict with:
            - success: True if import succeeded
            - package_path: Full content browser path of imported asset

        Examples:
            # Convert and export a 3D model to Unreal
            generate_3d(prompt="a tree") ->
            convert_3d_format(asset_id=..., target_format="fbx") ->
            export_to_unreal(asset_id=..., project_path="C:/Projects/MyGame/MyGame.uproject")
        """
        try:
            # Get the asset
            asset = asset_registry.get_asset(asset_id)
            if not asset:
                return {
                    "error": f"Asset {asset_id} not found or expired."
                }

            # Download the asset
            asset_url = asset.asset_url or asset.get_asset_url(asset_registry.comfyui_base_url)

            import tempfile
            ext = Path(asset.filename).suffix.lower() or ".png"

            # Check if format is supported by Unreal
            supported = [".fbx", ".obj", ".png", ".jpg", ".jpeg", ".tga", ".exr", ".hdr"]
            if ext not in supported:
                return {
                    "error": f"Format {ext} not directly supported by Unreal. "
                    f"Use convert_3d_format(asset_id, 'fbx') first for 3D models."
                }

            temp_dir = Path(tempfile.gettempdir()) / "comfyui_mcp_exports"
            temp_dir.mkdir(exist_ok=True)
            temp_path = temp_dir / f"{asset_id[:8]}{ext}"

            try:
                response = requests.get(asset_url, timeout=60)
                response.raise_for_status()
                with open(temp_path, "wb") as f:
                    f.write(response.content)
            except requests.RequestException as e:
                return {"error": f"Failed to download asset: {e}"}

            # Export to Unreal
            result = external_app_manager.export_to_unreal(temp_path, project_path, package_path)

            if "error" not in result:
                result["asset_id"] = asset_id

            return result

        except Exception as e:
            logger.exception(f"Failed to export to Unreal: {e}")
            return {"error": f"Failed to export to Unreal: {str(e)}"}

    @mcp.tool()
    def convert_3d_format(
        asset_id: str,
        target_format: str,
        output_dir: Optional[str] = None
    ) -> dict:
        """Convert a 3D asset to a different format using Blender.

        Useful for converting between glTF, FBX, and OBJ formats.
        Common use case: Convert glTF/GLB from generate_3d to FBX for Unreal Engine.

        **Requirements:**
        - Blender must be installed (required for conversion)

        **Supported formats:**
        - glb: Binary glTF (compact, recommended for web)
        - gltf: Text glTF with separate texture files
        - fbx: Autodesk FBX (best for Unreal Engine)
        - obj: Wavefront OBJ (legacy, wide compatibility)

        Args:
            asset_id: ID of the 3D asset to convert
            target_format: Target format (glb, gltf, fbx, obj)
            output_dir: Optional output directory. If not specified, uses temp directory.

        Returns:
            Dict with:
            - success: True if conversion succeeded
            - output_path: Path to converted file
            - source_format: Original format
            - target_format: Converted format
            - bytes_size: Size of converted file

        Examples:
            # Generate 3D model and convert to FBX for Unreal
            result = generate_3d(prompt="a sword")
            convert_3d_format(asset_id=result["asset_id"], target_format="fbx")

            # Convert GLB to OBJ for legacy software
            convert_3d_format(asset_id="abc123", target_format="obj")
        """
        try:
            # Get the asset
            asset = asset_registry.get_asset(asset_id)
            if not asset:
                return {
                    "error": f"Asset {asset_id} not found or expired."
                }

            # Validate it's a 3D asset
            ext = Path(asset.filename).suffix.lower()
            supported_3d = [".glb", ".gltf", ".fbx", ".obj"]
            if ext not in supported_3d:
                return {
                    "error": f"Asset is not a 3D file (extension: {ext}). "
                    f"Conversion supports: {supported_3d}"
                }

            # Download the asset
            asset_url = asset.asset_url or asset.get_asset_url(asset_registry.comfyui_base_url)

            import tempfile
            temp_dir = Path(tempfile.gettempdir()) / "comfyui_mcp_exports"
            temp_dir.mkdir(exist_ok=True)

            source_path = temp_dir / f"{asset_id[:8]}_source{ext}"

            try:
                response = requests.get(asset_url, timeout=60)
                response.raise_for_status()
                with open(source_path, "wb") as f:
                    f.write(response.content)
            except requests.RequestException as e:
                return {"error": f"Failed to download asset: {e}"}

            # Convert
            output_directory = Path(output_dir) if output_dir else temp_dir
            result = external_app_manager.convert_3d_format(
                source_path, target_format, output_directory
            )

            if "error" not in result:
                result["asset_id"] = asset_id

            return result

        except Exception as e:
            logger.exception(f"Failed to convert 3D format: {e}")
            return {"error": f"Failed to convert: {str(e)}"}

    @mcp.tool()
    def auto_rig_model(
        asset_id: str,
        rig_type: str = "humanoid",
        auto_weights: bool = True,
        generate_ik: bool = True,
        save_blend_file: bool = False,
        output_dir: Optional[str] = None
    ) -> dict:
        """Auto-rig a 3D model with a skeleton for animation.

        Creates an armature (skeleton) and automatically assigns vertex weights
        so the model can be posed and animated in Blender.

        **Rig Types:**
        - `humanoid`: Full humanoid rig with spine, arms, legs, hands, head.
          Uses Rigify (if available) for production-quality rig with IK/FK controls.
        - `biped_simple`: Simplified two-legged rig without Rigify dependency.
          Good for quick rigging of humanoid characters.
        - `quadruped`: Four-legged animal rig with spine, legs, tail, neck, head.
          Suitable for dogs, cats, horses, etc.
        - `simple`: Basic vertical spine chain. Good for snakes, worms,
          or objects that just need bendable segments.
        - `custom`: Define your own bone structure (advanced).

        **Requirements:**
        - Blender must be installed
        - For best results with humanoid, install Rigify addon (included with Blender)

        Args:
            asset_id: ID of the 3D asset to rig
            rig_type: Type of skeleton to create (humanoid, biped_simple, quadruped, simple)
            auto_weights: Automatically paint vertex weights (recommended)
            generate_ik: Add IK constraints for easier posing
            save_blend_file: Save the rigged model as a .blend file
            output_dir: Directory to save .blend file (if save_blend_file=True)

        Returns:
            Dict with:
            - success: True if rigging succeeded
            - rig_type: Type of rig created
            - output_path: Path to .blend file (if saved)
            - message: Status message

        Examples:
            # Generate and rig a character
            result = generate_3d(prompt="a fantasy warrior character")
            auto_rig_model(asset_id=result["asset_id"], rig_type="humanoid")

            # Rig an animal model
            result = generate_3d(prompt="a wolf")
            auto_rig_model(asset_id=result["asset_id"], rig_type="quadruped")

            # Simple rig for a snake
            auto_rig_model(asset_id="abc123", rig_type="simple")

            # Save rigged model for later use
            auto_rig_model(
                asset_id="abc123",
                rig_type="humanoid",
                save_blend_file=True,
                output_dir="C:/Models/Rigged"
            )
        """
        try:
            # Get the asset
            asset = asset_registry.get_asset(asset_id)
            if not asset:
                return {
                    "error": f"Asset {asset_id} not found or expired."
                }

            # Validate it's a 3D asset
            ext = Path(asset.filename).suffix.lower()
            supported_3d = [".glb", ".gltf", ".fbx", ".obj"]
            if ext not in supported_3d:
                return {
                    "error": f"Asset is not a 3D file (extension: {ext}). "
                    f"Auto-rigging supports: {supported_3d}"
                }

            # Download the asset
            asset_url = asset.asset_url or asset.get_asset_url(asset_registry.comfyui_base_url)

            import tempfile
            temp_dir = Path(tempfile.gettempdir()) / "comfyui_mcp_exports"
            temp_dir.mkdir(exist_ok=True)

            source_path = temp_dir / f"{asset_id[:8]}_rig{ext}"

            try:
                response = requests.get(asset_url, timeout=60)
                response.raise_for_status()
                with open(source_path, "wb") as f:
                    f.write(response.content)
            except requests.RequestException as e:
                return {"error": f"Failed to download asset: {e}"}

            # Determine output path
            output_path = None
            if save_blend_file:
                if output_dir:
                    out_dir = Path(output_dir)
                    out_dir.mkdir(parents=True, exist_ok=True)
                else:
                    out_dir = temp_dir
                output_path = out_dir / f"{asset_id[:8]}_{rig_type}_rigged.blend"

            # Run auto-rig
            result = external_app_manager.auto_rig_model(
                asset_path=source_path,
                rig_type=rig_type,
                auto_weights=auto_weights,
                generate_ik=generate_ik,
                output_path=output_path
            )

            if "error" not in result:
                result["asset_id"] = asset_id
                result["original_filename"] = asset.filename

            return result

        except Exception as e:
            logger.exception(f"Failed to auto-rig model: {e}")
            return {"error": f"Failed to auto-rig: {str(e)}"}

    @mcp.tool()
    def list_rig_types() -> dict:
        """List available rig types for auto_rig_model.

        Returns descriptions and use cases for each rig type.

        Returns:
            Dict with rig type information
        """
        return {
            "rig_types": [
                {
                    "type": "humanoid",
                    "name": "Humanoid (Rigify)",
                    "description": "Full humanoid rig using Blender's Rigify system",
                    "use_cases": ["Characters", "People", "Humanoid creatures", "Bipedal robots"],
                    "features": ["IK/FK switching", "Advanced controls", "Production-ready"],
                    "requirements": "Rigify addon (included with Blender)"
                },
                {
                    "type": "biped_simple",
                    "name": "Biped Simple",
                    "description": "Simplified two-legged rig without Rigify",
                    "use_cases": ["Quick character rigging", "Prototyping", "Simple bipeds"],
                    "features": ["Basic IK", "Symmetrical", "Fast setup"],
                    "requirements": "None"
                },
                {
                    "type": "quadruped",
                    "name": "Quadruped",
                    "description": "Four-legged animal rig",
                    "use_cases": ["Dogs", "Cats", "Horses", "Wolves", "Any 4-legged animal"],
                    "features": ["Spine chain", "4 legs with IK", "Tail", "Head/neck"],
                    "requirements": "None"
                },
                {
                    "type": "simple",
                    "name": "Simple Spine",
                    "description": "Basic vertical bone chain",
                    "use_cases": ["Snakes", "Worms", "Tentacles", "Ropes", "Bendy objects"],
                    "features": ["Configurable bone count", "Vertical chain"],
                    "requirements": "None"
                },
                {
                    "type": "custom",
                    "name": "Custom Bones",
                    "description": "Define your own bone structure",
                    "use_cases": ["Special rigs", "Mechanical objects", "Abstract shapes"],
                    "features": ["Full control over bone placement"],
                    "requirements": "Bone definitions in options"
                }
            ],
            "tips": [
                "For best results, ensure your model is in a T-pose or A-pose",
                "Model should be facing the +Y or -Y direction",
                "auto_weights works best on watertight meshes",
                "Use biped_simple if humanoid/Rigify has issues"
            ]
        }

    @mcp.tool()
    def animate_model(
        blend_file_path: str,
        animation_type: str = "idle",
        duration: float = 2.0,
        fps: int = 30,
        loop: bool = True,
        intensity: float = 1.0,
        output_format: str = "glb",
        output_dir: Optional[str] = None,
        render_video: bool = False
    ) -> dict:
        """Generate procedural animations for a rigged 3D model.

        Creates animations like walk cycles, idle breathing, jumps, and gestures.
        The model must already be rigged (use auto_rig_model first).

        **Animation Types:**
        - `walk`: Walking cycle with arm swing and hip sway
        - `run`: Running cycle with arm pumping and body lean
        - `idle`: Subtle breathing and weight shift (great for game idle states)
        - `wave`: Waving gesture with raised arm
        - `jump`: Complete jump: crouch, launch, air, land
        - `nod`: Head nodding animation
        - `look_around`: Looking left and right

        **Requirements:**
        - Blender must be installed
        - Model must be rigged (has an armature/skeleton)
        - Use auto_rig_model first if your model isn't rigged

        Args:
            blend_file_path: Path to a rigged .blend file
            animation_type: Type of animation (walk, run, idle, wave, jump, nod, look_around)
            duration: Animation duration in seconds
            fps: Frames per second (default: 30)
            loop: Make animation loop-friendly (default: True)
            intensity: Animation intensity (0.5=subtle, 1.0=normal, 1.5=exaggerated)
            output_format: Export format - glb, fbx, or blend (default: glb)
            output_dir: Directory to save animated model. If not specified, uses temp directory.
            render_video: Also render animation to MP4 video (default: False)

        Returns:
            Dict with:
            - success: True if animation was generated
            - output_path: Path to exported animated model
            - video_path: Path to video (if render_video=True)
            - animation_type: Type of animation created
            - duration: Animation duration
            - total_frames: Number of frames in animation

        Examples:
            # Rig a model and add a walk cycle
            result = generate_3d(prompt="a robot character")
            rig = auto_rig_model(asset_id=result["asset_id"], rig_type="humanoid", save_blend_file=True)
            animate_model(blend_file_path=rig["output_path"], animation_type="walk")

            # Create an idle animation for a game character
            animate_model(
                blend_file_path="C:/Models/character_rigged.blend",
                animation_type="idle",
                duration=3.0,
                loop=True
            )

            # Create exaggerated cartoon jump
            animate_model(
                blend_file_path="path/to/model.blend",
                animation_type="jump",
                intensity=1.5,
                render_video=True
            )
        """
        try:
            from pathlib import Path
            import tempfile

            blend_path = Path(blend_file_path)
            if not blend_path.exists():
                return {"error": f"Blend file not found: {blend_file_path}"}

            # Determine output path
            if output_dir:
                out_dir = Path(output_dir)
                out_dir.mkdir(parents=True, exist_ok=True)
            else:
                out_dir = Path(tempfile.gettempdir()) / "comfyui_mcp_animations"
                out_dir.mkdir(exist_ok=True)

            output_path = out_dir / f"{blend_path.stem}_{animation_type}.{output_format}"
            video_path = out_dir / f"{blend_path.stem}_{animation_type}.mp4" if render_video else None

            # Run animation
            result = external_app_manager.animate_model(
                blend_path=blend_path,
                animation_type=animation_type,
                duration=duration,
                fps=fps,
                loop=loop,
                intensity=intensity,
                output_path=output_path,
                output_format=output_format,
                render_video=render_video,
                video_path=video_path
            )

            return result

        except Exception as e:
            logger.exception(f"Failed to animate model: {e}")
            return {"error": f"Failed to animate: {str(e)}"}

    @mcp.tool()
    def list_animation_types() -> dict:
        """List available animation types for animate_model.

        Returns descriptions, recommended durations, and usage tips for each animation type.

        Returns:
            Dict with animation type information
        """
        return external_app_manager.list_animation_types()

    @mcp.tool()
    def import_mocap(
        blend_file_path: str,
        mocap_file_path: str,
        scale: float = 1.0,
        start_frame: int = 1,
        use_fps_scale: bool = True,
        output_format: str = "glb",
        output_dir: Optional[str] = None
    ) -> dict:
        """Import motion capture data (BVH/FBX) and apply to a rigged model.

        Imports BVH or FBX motion capture files and retargets the animation
        to the character's existing rig. Supports Mixamo and CMU mocap formats.

        **Supported Motion Capture Formats:**
        - BVH (Biovision Hierarchy) - Common mocap format, used by Mixamo free downloads
        - FBX with animation data

        **Getting Free Mocap Data:**
        - Mixamo (mixamo.com): Free mocap library, download as BVH
        - CMU Motion Capture Database: Academic mocap in BVH format
        - Rokoko: Free sample animations

        **Requirements:**
        - Blender must be installed
        - Model must already be rigged (use auto_rig_model first)
        - For best results, use humanoid rigs with standard bone names

        Args:
            blend_file_path: Path to a rigged .blend file
            mocap_file_path: Path to BVH or FBX motion capture file
            scale: Scale factor for mocap data (default: 1.0)
            start_frame: Start frame for the animation (default: 1)
            use_fps_scale: Scale animation to match scene FPS (default: True)
            output_format: Export format - glb, fbx, or blend (default: glb)
            output_dir: Directory to save animated model. If not specified, uses temp directory.

        Returns:
            Dict with:
            - success: True if mocap was imported
            - output_path: Path to exported animated model
            - mocap_format: Format of imported mocap (BVH/FBX)
            - message: Status message

        Examples:
            # Rig a model and import a Mixamo walk animation
            result = generate_3d(prompt="a human character")
            rig = auto_rig_model(asset_id=result["asset_id"], rig_type="humanoid", save_blend_file=True)
            import_mocap(
                blend_file_path=rig["output_path"],
                mocap_file_path="C:/Mocap/mixamo_walk.bvh"
            )

            # Import CMU mocap to an existing rigged model
            import_mocap(
                blend_file_path="C:/Models/character_rigged.blend",
                mocap_file_path="C:/Mocap/cmu_run.bvh",
                scale=0.01  # CMU data may need scaling
            )
        """
        try:
            from pathlib import Path
            import tempfile

            blend_path = Path(blend_file_path)
            mocap_path = Path(mocap_file_path)

            if not blend_path.exists():
                return {"error": f"Blend file not found: {blend_file_path}"}

            if not mocap_path.exists():
                return {"error": f"Mocap file not found: {mocap_file_path}"}

            # Validate mocap format
            mocap_ext = mocap_path.suffix.lower()
            if mocap_ext not in [".bvh", ".fbx"]:
                return {"error": f"Unsupported mocap format: {mocap_ext}. Supported: .bvh, .fbx"}

            # Determine output path
            if output_dir:
                out_dir = Path(output_dir)
                out_dir.mkdir(parents=True, exist_ok=True)
            else:
                out_dir = Path(tempfile.gettempdir()) / "comfyui_mcp_mocap"
                out_dir.mkdir(exist_ok=True)

            output_path = out_dir / f"{blend_path.stem}_{mocap_path.stem}.{output_format}"

            # Run mocap import
            result = external_app_manager.import_mocap(
                blend_path=blend_path,
                mocap_path=mocap_path,
                scale=scale,
                start_frame=start_frame,
                use_fps_scale=use_fps_scale,
                output_path=output_path,
                output_format=output_format
            )

            return result

        except Exception as e:
            logger.exception(f"Failed to import mocap: {e}")
            return {"error": f"Failed to import mocap: {str(e)}"}

    @mcp.tool()
    def smart_rig_model(
        asset_id: str,
        backend: str = "auto",
        rig_type: str = "humanoid",
        save_output: bool = True,
        output_dir: Optional[str] = None
    ) -> dict:
        """Smart auto-rigging with multiple AI backends.

        Uses the best available rigging backend with automatic fallback:
        1. **UniRig AI** (best quality) - Open source, requires local installation
        2. **Tripo3D Cloud** - Cloud API, requires API key
        3. **Rigify** - Blender built-in, always available

        **Backend Details:**
        - `unirig`: VAST-AI's UniRig uses autoregressive AI for 215% better accuracy
        - `tripo`: Tripo3D cloud service with AI rigging and animation presets
        - `rigify`: Blender's production-quality rigging system
        - `auto`: Automatically tries backends in order of quality

        Args:
            asset_id: ID of the 3D asset to rig
            backend: Rigging backend - "auto", "unirig", "tripo", or "rigify"
            rig_type: Type of rig (humanoid, quadruped, simple)
            save_output: Save the rigged model to disk
            output_dir: Directory to save output (if save_output=True)

        Returns:
            Dict with:
            - success: True if rigging succeeded
            - backend_used: Which backend performed the rigging
            - output_path: Path to rigged model
            - message: Status message

        Examples:
            # Auto-select best available backend
            smart_rig_model(asset_id="abc123", backend="auto")

            # Force UniRig (if installed)
            smart_rig_model(asset_id="abc123", backend="unirig")

            # Use cloud rigging
            smart_rig_model(asset_id="abc123", backend="tripo")
        """
        try:
            # Get the asset
            asset = asset_registry.get_asset(asset_id)
            if not asset:
                return {"error": f"Asset {asset_id} not found or expired."}

            # Validate it's a 3D asset
            ext = Path(asset.filename).suffix.lower()
            supported_3d = [".glb", ".gltf", ".fbx", ".obj"]
            if ext not in supported_3d:
                return {
                    "error": f"Asset is not a 3D file (extension: {ext}). "
                    f"Smart rigging supports: {supported_3d}"
                }

            # Download the asset
            asset_url = asset.asset_url or asset.get_asset_url(asset_registry.comfyui_base_url)

            import tempfile
            temp_dir = Path(tempfile.gettempdir()) / "comfyui_mcp_exports"
            temp_dir.mkdir(exist_ok=True)

            source_path = temp_dir / f"{asset_id[:8]}_smartrig{ext}"

            try:
                response = requests.get(asset_url, timeout=60)
                response.raise_for_status()
                with open(source_path, "wb") as f:
                    f.write(response.content)
            except requests.RequestException as e:
                return {"error": f"Failed to download asset: {e}"}

            # Determine output path
            output_path = None
            if save_output:
                if output_dir:
                    out_dir = Path(output_dir)
                    out_dir.mkdir(parents=True, exist_ok=True)
                else:
                    out_dir = temp_dir
                output_path = out_dir / f"{asset_id[:8]}_{backend}_rigged.blend"

            # Run smart rigging
            result = external_app_manager.smart_rig_model(
                asset_path=source_path,
                backend=backend,
                rig_type=rig_type,
                output_path=output_path
            )

            if "error" not in result:
                result["asset_id"] = asset_id
                result["original_filename"] = asset.filename

            return result

        except Exception as e:
            logger.exception(f"Failed to smart-rig model: {e}")
            return {"error": f"Failed to rig: {str(e)}"}

    @mcp.tool()
    def get_rigging_backends() -> dict:
        """Get status of available rigging backends.

        Shows which rigging backends (UniRig, Tripo3D, Rigify) are installed
        and configured, with recommendations.

        Returns:
            Dict with:
            - backends: Status of each backend (available, type, description)
            - recommended: Recommended backend to use

        Examples:
            get_rigging_backends()
            # Returns: {"backends": {"unirig": {...}, "tripo": {...}}, "recommended": "unirig"}
        """
        return external_app_manager.get_rigging_backends()

    @mcp.tool()
    def tripo_rig_and_animate(
        asset_id: str,
        animation: str = "preset:walk",
        output_dir: Optional[str] = None
    ) -> dict:
        """Rig and animate a model using Tripo3D cloud service.

        One-step workflow that rigs a model AND applies an animation preset
        using Tripo3D's cloud AI.

        **Animation Presets:**
        - preset:idle - Standing idle
        - preset:walk - Walking cycle
        - preset:run - Running cycle
        - preset:jump - Jump animation
        - preset:dance - Dance animation
        - preset:wave - Waving gesture
        - preset:attack - Combat animation
        - preset:die - Death animation

        **Requirements:**
        - TRIPO_API_KEY environment variable must be set
        - Get API key from: https://platform.tripo3d.ai/

        Args:
            asset_id: ID of the 3D asset
            animation: Animation preset (e.g., "preset:walk")
            output_dir: Directory to save output files

        Returns:
            Dict with paths to rigged and animated models

        Examples:
            # Rig and add walk animation
            tripo_rig_and_animate(asset_id="abc123", animation="preset:walk")

            # Rig and add dance animation
            tripo_rig_and_animate(asset_id="abc123", animation="preset:dance")
        """
        try:
            from managers.tripo_client import TripoClientSync

            client = TripoClientSync()
            if not client.is_configured:
                return {
                    "error": "Tripo3D API key not configured. Set TRIPO_API_KEY environment variable.",
                    "help": "Get API key from: https://platform.tripo3d.ai/"
                }

            # Get the asset
            asset = asset_registry.get_asset(asset_id)
            if not asset:
                return {"error": f"Asset {asset_id} not found or expired."}

            # Download the asset
            asset_url = asset.asset_url or asset.get_asset_url(asset_registry.comfyui_base_url)
            ext = Path(asset.filename).suffix.lower()

            import tempfile
            temp_dir = Path(tempfile.gettempdir()) / "comfyui_mcp_tripo"
            temp_dir.mkdir(exist_ok=True)

            source_path = temp_dir / f"{asset_id[:8]}{ext}"

            try:
                response = requests.get(asset_url, timeout=60)
                response.raise_for_status()
                with open(source_path, "wb") as f:
                    f.write(response.content)
            except requests.RequestException as e:
                return {"error": f"Failed to download asset: {e}"}

            # Determine output directory
            out_dir = Path(output_dir) if output_dir else temp_dir

            # Run rig and animate
            result = client.rig_and_animate(
                model_path=source_path,
                animation=animation,
                output_dir=out_dir
            )

            if "error" not in result:
                result["asset_id"] = asset_id

            return result

        except ImportError:
            return {"error": "Tripo3D client not available. Check installation."}
        except Exception as e:
            logger.exception(f"Failed Tripo3D rig and animate: {e}")
            return {"error": str(e)}

    @mcp.tool()
    def list_tripo_animations() -> dict:
        """List available Tripo3D animation presets.

        Returns the animation presets available from Tripo3D's cloud service.

        Returns:
            Dict with animation preset information
        """
        try:
            from managers.tripo_client import TripoClientSync
            client = TripoClientSync()
            return {
                "presets": client.list_animation_presets(),
                "configured": client.is_configured,
                "note": "Set TRIPO_API_KEY to use these animations"
            }
        except ImportError:
            return {"error": "Tripo3D client not available"}

    logger.info("Registered external tools: get_external_app_status, export_to_blender, export_to_unreal, convert_3d_format, auto_rig_model, list_rig_types, animate_model, list_animation_types, import_mocap, smart_rig_model, get_rigging_backends, tripo_rig_and_animate, list_tripo_animations")

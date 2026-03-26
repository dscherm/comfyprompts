"""Property groups for ComfyUI MCP Blender addon."""

import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
)
from bpy.types import AddonPreferences, PropertyGroup


# =============================================================================
# ADDON PREFERENCES
# =============================================================================

class ComfyMCPPreferences(AddonPreferences):
    bl_idname = __package__

    mcp_host: StringProperty(name="MCP Server Host", default="127.0.0.1")
    mcp_port: IntProperty(name="MCP Server Port", default=9000, min=1, max=65535)
    comfyui_url: StringProperty(
        name="ComfyUI URL",
        default="http://127.0.0.1:8188",
        description="URL of the ComfyUI server",
    )
    tripo_api_key: StringProperty(name="Tripo3D API Key", default="", subtype='PASSWORD')
    unirig_path: StringProperty(name="UniRig Path", default="", subtype='DIR_PATH')
    output_dir: StringProperty(name="Output Directory", default="", subtype='DIR_PATH')

    def draw(self, context):
        layout = self.layout
        layout.label(text="ComfyUI Connection:")
        layout.prop(self, "comfyui_url")
        layout.separator()
        layout.label(text="MCP Server Connection:")
        row = layout.row()
        row.prop(self, "mcp_host")
        row.prop(self, "mcp_port")
        layout.separator()
        layout.label(text="Rigging Backends:")
        layout.prop(self, "tripo_api_key")
        layout.prop(self, "unirig_path")
        layout.separator()
        layout.prop(self, "output_dir")


# =============================================================================
# PROPERTY GROUPS
# =============================================================================

class ComfyMCPRiggingProps(PropertyGroup):
    rig_type: EnumProperty(
        name="Rig Type",
        items=[
            ('HUMANOID', "Humanoid", "Full humanoid rig"),
            ('BIPED_SIMPLE', "Biped Simple", "Simplified two-legged rig"),
            ('QUADRUPED', "Quadruped", "Four-legged animal rig"),
            ('SIMPLE', "Simple Spine", "Basic bone chain"),
        ],
        default='HUMANOID'
    )
    rig_backend: EnumProperty(
        name="Backend",
        items=[
            ('RIGIFY', "Rigify", "Blender's Rigify system"),
            ('UNIRIG', "UniRig AI", "VAST-AI UniRig"),
            ('TRIPO', "Tripo3D Cloud", "Cloud AI rigging"),
        ],
        default='RIGIFY'
    )
    auto_weights: BoolProperty(name="Auto Weights", default=True)
    generate_ik: BoolProperty(name="Generate IK", default=True)


class ComfyMCPAnimationProps(PropertyGroup):
    animation_type: EnumProperty(
        name="Animation",
        items=[
            ('walk', "Walk", "Walking cycle"),
            ('run', "Run", "Running cycle"),
            ('idle', "Idle", "Breathing/idle"),
            ('wave', "Wave", "Waving gesture"),
            ('jump', "Jump", "Jump animation"),
            ('nod', "Nod", "Head nodding"),
            ('look_around', "Look Around", "Looking left/right"),
        ],
        default='idle'
    )
    duration: FloatProperty(name="Duration", default=2.0, min=0.1, max=30.0, unit='TIME')
    fps: IntProperty(name="FPS", default=30, min=12, max=120)
    intensity: FloatProperty(name="Intensity", default=1.0, min=0.1, max=2.0)
    loop: BoolProperty(name="Loop", default=True)


class ComfyMCPMocapProps(PropertyGroup):
    mocap_file: StringProperty(name="Mocap File", default="", subtype='FILE_PATH')
    scale: FloatProperty(name="Scale", default=1.0, min=0.001, max=100.0)
    start_frame: IntProperty(name="Start Frame", default=1, min=1)
    use_fps_scale: BoolProperty(name="Scale to FPS", default=True)


class ComfyMCPExportProps(PropertyGroup):
    export_format: EnumProperty(
        name="Format",
        items=[
            ('GLB', "GLB", "Binary glTF"),
            ('FBX', "FBX", "Autodesk FBX"),
            ('BLEND', "Blend", "Blender native"),
        ],
        default='GLB'
    )
    include_animation: BoolProperty(name="Include Animation", default=True)


class ComfyMCPServerProps(PropertyGroup):
    """Properties for MCP server integration."""

    # --- Connection state ---
    mcp_connected: BoolProperty(name="MCP Connected", default=False)

    # --- Last generation result ---
    mcp_last_asset_id: StringProperty(
        name="Last Asset ID",
        default="",
        description="Asset ID from the last MCP generation",
    )
    mcp_job_status: StringProperty(name="MCP Status", default="Idle")

    # --- Workflow selection ---
    mcp_workflow: StringProperty(
        name="Workflow",
        default="generate_image",
        description="MCP workflow ID to use for generation",
    )

    # --- Upscale settings ---
    upscale_factor: IntProperty(
        name="Scale",
        default=2,
        min=2,
        max=4,
        description="Upscale factor (2x or 4x)",
    )

    # --- Variation settings ---
    variation_count: IntProperty(
        name="Count",
        default=4,
        min=1,
        max=8,
        description="Number of variations to generate",
    )
    variation_strength: FloatProperty(
        name="Strength",
        default=0.7,
        min=0.0,
        max=1.0,
        description="How different variations are from original (0=identical, 1=very different)",
    )

    # --- Style presets ---
    selected_style: StringProperty(
        name="Style",
        default="",
        description="Selected style preset ID",
    )
    available_styles: StringProperty(
        name="Styles JSON",
        default="[]",
        description="JSON array of available style presets (internal)",
    )

    # --- Model / workflow cache ---
    available_models: StringProperty(name="Models JSON", default="[]")
    available_workflows: StringProperty(name="Workflows JSON", default="[]")


class ComfyMCPPipelineProps(PropertyGroup):
    # --- Pipeline mode ---
    pipeline_mode: EnumProperty(
        name="Mode",
        items=[
            ('IMG2IMG', "Image to Image", "Transform a rendered image with AI"),
            ('TXT2IMG', "Text to Image", "Generate an image from text"),
        ],
        default='IMG2IMG',
    )

    # --- Prompts ---
    prompt: StringProperty(
        name="Prompt",
        default="",
        description="Text prompt describing the desired output",
    )
    negative_prompt: StringProperty(
        name="Negative",
        default="blurry, low quality, distorted",
        description="Things to avoid in the generation",
    )

    # --- Generation parameters ---
    checkpoint: StringProperty(
        name="Checkpoint",
        default="v1-5-pruned-emaonly.ckpt",
        description="Model checkpoint filename",
    )
    steps: IntProperty(name="Steps", default=20, min=1, max=150)
    cfg: FloatProperty(name="CFG Scale", default=7.0, min=1.0, max=30.0)
    denoise: FloatProperty(
        name="Denoise",
        default=0.65,
        min=0.0,
        max=1.0,
        description="Denoising strength (lower = closer to original)",
    )
    seed: IntProperty(
        name="Seed",
        default=0,
        min=0,
        description="Random seed (0 = random)",
    )
    sampler: StringProperty(name="Sampler", default="euler")
    scheduler: StringProperty(name="Scheduler", default="normal")

    # --- Capture settings ---
    capture_width: IntProperty(name="Width", default=512, min=64, max=2048)
    capture_height: IntProperty(name="Height", default=512, min=64, max=2048)

    # --- Input / output paths ---
    input_image_path: StringProperty(name="Input Image", default="", subtype='FILE_PATH')
    output_image_path: StringProperty(name="Output Image", default="", subtype='FILE_PATH')

    # --- Job state ---
    comfyui_connected: BoolProperty(name="Connected", default=False)
    job_prompt_id: StringProperty(name="Prompt ID", default="")
    job_status: StringProperty(name="Status", default="Idle")
    job_progress: StringProperty(name="Progress", default="")
    poll_interval: IntProperty(
        name="Poll Interval (ms)",
        default=2000,
        min=500,
        max=10000,
        description="How often to check job status",
    )

"""Property groups for ComfyUI Blender addon."""

import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
)
from bpy.types import PropertyGroup


# =============================================================================
# WORKFLOW CACHE (for dynamic workflow enum)
# =============================================================================

_workflow_cache = []
_workflow_cache_valid = False


def get_workflow_cache():
    global _workflow_cache
    return _workflow_cache


def set_workflow_cache(workflows):
    global _workflow_cache, _workflow_cache_valid
    _workflow_cache = workflows
    _workflow_cache_valid = True


def is_workflow_cache_valid():
    global _workflow_cache_valid
    return _workflow_cache_valid


def invalidate_workflow_cache():
    global _workflow_cache_valid
    _workflow_cache_valid = False


def _get_workflow_items(self, context):
    """Get available workflows as enum items."""
    global _workflow_cache

    if _workflow_cache:
        items = []
        for filename, info in _workflow_cache:
            workflow_type = info.get('type', 'unknown')
            desc = info.get('description', filename)
            if '3d' in workflow_type.lower() or '3d' in filename.lower():
                name = desc if len(desc) < 40 else desc[:37] + '...'
                items.append((filename, name, desc))
        if items:
            return items

    return [
        ('triposg_image_to_3d.json', 'TripoSG (Fast)', 'Fast 3D generation (~2 min)'),
        ('triposg_simple.json', 'TripoSG Simple', 'Simplified fast 3D generation'),
        ('hy3d_example_01 (1) - Copy.json', 'Hunyuan3D (Quality)', 'High quality 3D with textures'),
        ('TripoSG.json', 'TripoSG Full', 'Full-featured TripoSG workflow'),
    ]


def _get_input_mode_items(self, context):
    return [
        ('VIEWPORT', 'Viewport Capture', 'Capture current 3D viewport'),
        ('RENDER', 'Render Result', 'Use last render result'),
        ('FILE', 'Image File', 'Load external image file'),
        ('TEXT', 'Text Prompt', 'Generate from text description'),
    ]


# =============================================================================
# GENERATION PROPERTIES
# =============================================================================

class ComfyUIGenerationProps(PropertyGroup):
    input_mode: EnumProperty(
        name="Input Mode",
        description="How to provide input for 3D generation",
        items=_get_input_mode_items,
        default=0,
    )
    text_prompt: StringProperty(
        name="Prompt",
        description="Text description for generation",
        default="",
    )
    image_path: StringProperty(
        name="Image",
        description="Path to input image file",
        default="",
        subtype='FILE_PATH',
    )
    workflow: EnumProperty(
        name="Workflow",
        description="3D generation workflow to use",
        items=_get_workflow_items,
        default=0,
    )
    recommended_workflow: StringProperty(
        name="Recommended Workflow",
        default="",
    )
    job_id: StringProperty(name="Job ID", default="")
    job_status: StringProperty(name="Status", default="Ready")
    job_progress: FloatProperty(
        name="Progress",
        default=0.0, min=0.0, max=100.0,
        subtype='PERCENTAGE',
    )
    output_path: StringProperty(name="Output", default="")
    auto_import: BoolProperty(
        name="Auto Import",
        description="Automatically import GLB when generation completes",
        default=True,
    )
    ai_reasoning: StringProperty(name="AI Reasoning", default="")
    api_connected: BoolProperty(name="API Connected", default=False)
    comfyui_connected: BoolProperty(name="ComfyUI Connected", default=False)
    workflows_loaded: BoolProperty(name="Workflows Loaded", default=False)


# =============================================================================
# RIGGING PROPERTIES
# =============================================================================

class ComfyUIRiggingProps(PropertyGroup):
    rig_type: EnumProperty(
        name="Rig Type",
        items=[
            ('HUMANOID', "Humanoid", "Full humanoid rig"),
            ('BIPED_SIMPLE', "Biped Simple", "Simplified two-legged rig"),
            ('QUADRUPED', "Quadruped", "Four-legged animal rig"),
            ('SIMPLE', "Simple Spine", "Basic bone chain"),
        ],
        default='HUMANOID',
    )
    rig_backend: EnumProperty(
        name="Backend",
        items=[
            ('RIGIFY', "Rigify", "Blender's Rigify system"),
            ('UNIRIG', "UniRig AI", "VAST-AI UniRig"),
            ('TRIPO', "Tripo3D Cloud", "Cloud AI rigging"),
        ],
        default='RIGIFY',
    )
    auto_weights: BoolProperty(name="Auto Weights", default=True)
    generate_ik: BoolProperty(name="Generate IK", default=True)


# =============================================================================
# ANIMATION PROPERTIES
# =============================================================================

class ComfyUIAnimationProps(PropertyGroup):
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
        default='idle',
    )
    duration: FloatProperty(name="Duration", default=2.0, min=0.1, max=30.0, unit='TIME')
    fps: IntProperty(name="FPS", default=30, min=12, max=120)
    intensity: FloatProperty(name="Intensity", default=1.0, min=0.1, max=2.0)
    loop: BoolProperty(name="Loop", default=True)


# =============================================================================
# MOCAP PROPERTIES
# =============================================================================

class ComfyUIMocapProps(PropertyGroup):
    mocap_file: StringProperty(name="Mocap File", default="", subtype='FILE_PATH')
    scale: FloatProperty(name="Scale", default=1.0, min=0.001, max=100.0)
    start_frame: IntProperty(name="Start Frame", default=1, min=1)
    use_fps_scale: BoolProperty(name="Scale to FPS", default=True)


# =============================================================================
# EXPORT PROPERTIES
# =============================================================================

class ComfyUIExportProps(PropertyGroup):
    export_format: EnumProperty(
        name="Format",
        items=[
            ('GLB', "GLB", "Binary glTF"),
            ('FBX', "FBX", "Autodesk FBX"),
            ('BLEND', "Blend", "Blender native"),
        ],
        default='GLB',
    )
    include_animation: BoolProperty(name="Include Animation", default=True)

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
    tripo_api_key: StringProperty(name="Tripo3D API Key", default="", subtype='PASSWORD')
    unirig_path: StringProperty(name="UniRig Path", default="", subtype='DIR_PATH')
    output_dir: StringProperty(name="Output Directory", default="", subtype='DIR_PATH')

    def draw(self, context):
        layout = self.layout
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

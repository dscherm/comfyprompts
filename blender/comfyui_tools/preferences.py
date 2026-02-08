"""Unified addon preferences for ComfyUI Blender addon."""

import bpy
from bpy.props import BoolProperty, IntProperty, StringProperty
from bpy.types import AddonPreferences


class ComfyUIPreferences(AddonPreferences):
    bl_idname = __package__

    # --- Generation / Prompter API ---
    api_url: StringProperty(
        name="Prompter API URL",
        description="URL of the ComfyUI Prompter API server",
        default="http://127.0.0.1:5050",
    )
    output_folder: StringProperty(
        name="Output Folder",
        description="Path to ComfyUI 3D output folder",
        default="C:/ComfyUI/output/3D",
        subtype='DIR_PATH',
    )
    auto_import: BoolProperty(
        name="Auto Import GLB",
        description="Automatically import generated GLB files when complete",
        default=True,
    )
    auto_refresh_workflows: BoolProperty(
        name="Auto Refresh Workflows",
        description="Automatically fetch workflows when connecting",
        default=True,
    )
    capture_resolution_x: IntProperty(
        name="Capture Width",
        description="Width of viewport capture",
        default=512, min=256, max=2048,
    )
    capture_resolution_y: IntProperty(
        name="Capture Height",
        description="Height of viewport capture",
        default=512, min=256, max=2048,
    )
    poll_interval: IntProperty(
        name="Poll Interval (ms)",
        description="How often to check generation job status",
        default=2000, min=500, max=10000,
    )

    # --- MCP Server ---
    mcp_host: StringProperty(
        name="MCP Server Host",
        description="Hostname of the MCP server for rigging backends",
        default="127.0.0.1",
    )
    mcp_port: IntProperty(
        name="MCP Server Port",
        description="Port of the MCP server",
        default=9000, min=1, max=65535,
    )

    # --- Rigging ---
    tripo_api_key: StringProperty(
        name="Tripo3D API Key",
        default="",
        subtype='PASSWORD',
    )
    unirig_path: StringProperty(
        name="UniRig Path",
        default="",
        subtype='DIR_PATH',
    )

    def draw(self, context):
        layout = self.layout

        # Generation API
        box = layout.box()
        box.label(text="Generation API (Prompter)", icon='URL')
        box.prop(self, "api_url")
        box.prop(self, "output_folder")

        # MCP Server
        box = layout.box()
        box.label(text="MCP Server (Rigging)", icon='LINKED')
        row = box.row()
        row.prop(self, "mcp_host")
        row.prop(self, "mcp_port")

        # Import settings
        box = layout.box()
        box.label(text="Import Settings", icon='IMPORT')
        box.prop(self, "auto_import")
        box.prop(self, "auto_refresh_workflows")

        # Capture settings
        box = layout.box()
        box.label(text="Viewport Capture", icon='RENDER_STILL')
        row = box.row()
        row.prop(self, "capture_resolution_x", text="Width")
        row.prop(self, "capture_resolution_y", text="Height")

        # Rigging backends
        box = layout.box()
        box.label(text="Rigging Backends", icon='ARMATURE_DATA')
        box.prop(self, "tripo_api_key")
        box.prop(self, "unirig_path")

        # Advanced
        box = layout.box()
        box.label(text="Advanced", icon='PREFERENCES')
        box.prop(self, "poll_interval")


def get_preferences():
    """Get addon preferences."""
    addon = bpy.context.preferences.addons.get(__package__)
    if addon:
        return addon.preferences
    return None

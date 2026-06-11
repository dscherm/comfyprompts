"""Tests for Blender-specific parametric workflows (depth, normal, pose)."""

import json
import pytest
from pathlib import Path
from managers.workflow_manager import WorkflowManager


REPO_ROOT = Path(__file__).parent.parent.parent.parent
WORKFLOWS_DIR = REPO_ROOT / "workflows" / "mcp"

BLENDER_WORKFLOWS = [
    "blender_depth_guided",
    "blender_normal_texturing",
    "blender_pose_to_render",
]


@pytest.fixture
def workflow_manager():
    """Create a WorkflowManager pointing at the repo-root workflows/mcp/ dir."""
    return WorkflowManager(WORKFLOWS_DIR)


class TestBlenderWorkflowFiles:
    """Validate Blender workflow JSON files on disk."""

    @pytest.mark.parametrize("name", BLENDER_WORKFLOWS)
    def test_json_file_exists(self, name):
        assert (WORKFLOWS_DIR / f"{name}.json").exists()

    @pytest.mark.parametrize("name", BLENDER_WORKFLOWS)
    def test_meta_file_exists(self, name):
        assert (WORKFLOWS_DIR / f"{name}.meta.json").exists()

    @pytest.mark.parametrize("name", BLENDER_WORKFLOWS)
    def test_json_valid(self, name):
        with open(WORKFLOWS_DIR / f"{name}.json") as f:
            data = json.load(f)
        assert isinstance(data, dict)
        assert len(data) > 0

    @pytest.mark.parametrize("name", BLENDER_WORKFLOWS)
    def test_meta_valid(self, name):
        with open(WORKFLOWS_DIR / f"{name}.meta.json") as f:
            meta = json.load(f)
        assert "name" in meta
        assert "description" in meta
        assert "requirements" in meta
        assert "parameters" in meta
        assert "output" in meta

    @pytest.mark.parametrize("name", BLENDER_WORKFLOWS)
    def test_all_nodes_have_class_type(self, name):
        with open(WORKFLOWS_DIR / f"{name}.json") as f:
            data = json.load(f)
        for node_id, node in data.items():
            if isinstance(node, dict) and "inputs" in node:
                assert "class_type" in node, f"Node {node_id} missing class_type"

    @pytest.mark.parametrize("name", BLENDER_WORKFLOWS)
    def test_no_custom_nodes_required(self, name):
        """Blender workflows use only built-in ComfyUI nodes (no custom nodes)."""
        with open(WORKFLOWS_DIR / f"{name}.meta.json") as f:
            meta = json.load(f)
        custom = meta.get("requirements", {}).get("custom_nodes", {})
        assert len(custom) == 0, f"Blender workflow should not require custom nodes: {custom}"

    @pytest.mark.parametrize("name", BLENDER_WORKFLOWS)
    def test_uses_locally_available_checkpoint(self, name):
        """Blender workflows target an installed checkpoint — unless the meta
        documents a pending download (requires_download), in which case the
        documented SD1.5 stack is expected."""
        with open(WORKFLOWS_DIR / f"{name}.meta.json") as f:
            meta = json.load(f)
        checkpoint = meta["requirements"]["models"]["checkpoint"]
        if meta.get("requires_download"):
            assert "v1-5" in checkpoint or "sd15" in checkpoint.lower()
        else:
            assert checkpoint == "sd_xl_base_1.0.safetensors"

    @pytest.mark.parametrize("name", BLENDER_WORKFLOWS)
    def test_has_blender_category(self, name):
        with open(WORKFLOWS_DIR / f"{name}.meta.json") as f:
            meta = json.load(f)
        assert meta.get("category") == "blender"

    @pytest.mark.parametrize("name", BLENDER_WORKFLOWS)
    def test_has_blender_tag(self, name):
        with open(WORKFLOWS_DIR / f"{name}.meta.json") as f:
            meta = json.load(f)
        assert "blender" in meta.get("tags", [])


class TestBlenderWorkflowDiscovery:
    """Test WorkflowManager discovers and parses Blender workflows."""

    def test_blender_workflows_discovered(self, workflow_manager):
        tool_names = [d.tool_name for d in workflow_manager.tool_definitions]
        for name in BLENDER_WORKFLOWS:
            assert name in tool_names, f"WorkflowManager did not discover: {name}"

    def test_depth_guided_params(self, workflow_manager):
        defn = next(
            (d for d in workflow_manager.tool_definitions if d.tool_name == "blender_depth_guided"),
            None,
        )
        assert defn is not None
        params = list(defn.parameters.keys())
        assert "depth_image" in params
        assert "source_image" in params
        assert "prompt" in params
        assert "controlnet_strength" in params
        assert defn.parameters["depth_image"].required
        assert defn.parameters["source_image"].required
        assert defn.parameters["prompt"].required
        assert not defn.parameters["controlnet_strength"].required

    def test_normal_texturing_params(self, workflow_manager):
        defn = next(
            (d for d in workflow_manager.tool_definitions if d.tool_name == "blender_normal_texturing"),
            None,
        )
        assert defn is not None
        params = list(defn.parameters.keys())
        assert "normal_image" in params
        assert "prompt" in params
        assert "width" in params
        assert "height" in params
        assert defn.parameters["normal_image"].required
        assert defn.parameters["prompt"].required
        assert not defn.parameters["width"].required
        assert not defn.parameters["height"].required

    def test_pose_to_render_params(self, workflow_manager):
        defn = next(
            (d for d in workflow_manager.tool_definitions if d.tool_name == "blender_pose_to_render"),
            None,
        )
        assert defn is not None
        params = list(defn.parameters.keys())
        assert "pose_image" in params
        assert "prompt" in params
        assert "width" in params
        assert "height" in params
        assert defn.parameters["pose_image"].required
        assert defn.parameters["prompt"].required

    def test_controlnet_strength_type(self, workflow_manager):
        """All Blender workflows should have controlnet_strength as float."""
        for name in BLENDER_WORKFLOWS:
            defn = next(d for d in workflow_manager.tool_definitions if d.tool_name == name)
            param = defn.parameters["controlnet_strength"]
            assert param.annotation is float

    def test_all_have_save_image_output(self, workflow_manager):
        """All Blender workflows output images via SaveImage node."""
        for name in BLENDER_WORKFLOWS:
            defn = next(d for d in workflow_manager.tool_definitions if d.tool_name == name)
            assert len(defn.output_preferences) > 0


class TestBlenderWorkflowRendering:
    """Test parameter substitution for Blender workflows."""

    def _get_defn(self, workflow_manager, name):
        return next(d for d in workflow_manager.tool_definitions if d.tool_name == name)

    def test_render_depth_guided(self, workflow_manager):
        defn = self._get_defn(workflow_manager, "blender_depth_guided")
        rendered = workflow_manager.render_workflow(defn, {
            "prompt": "oil painting of a medieval castle",
            "depth_image": "depth_001.png",
            "source_image": "render_001.png",
        })
        assert rendered is not None
        assert rendered["6"]["inputs"]["text"] == "oil painting of a medieval castle"
        assert rendered["3"]["inputs"]["image"] == "depth_001.png"
        assert rendered["4"]["inputs"]["image"] == "render_001.png"

    def test_render_normal_texturing(self, workflow_manager):
        defn = self._get_defn(workflow_manager, "blender_normal_texturing")
        rendered = workflow_manager.render_workflow(defn, {
            "prompt": "weathered stone texture, mossy cracks",
            "normal_image": "normals_001.png",
            "width": 512,
            "height": 512,
        })
        assert rendered is not None
        assert rendered["5"]["inputs"]["text"] == "weathered stone texture, mossy cracks"
        assert rendered["3"]["inputs"]["image"] == "normals_001.png"
        assert rendered["4"]["inputs"]["width"] == 512
        assert rendered["4"]["inputs"]["height"] == 512

    def test_render_pose_to_render(self, workflow_manager):
        defn = self._get_defn(workflow_manager, "blender_pose_to_render")
        rendered = workflow_manager.render_workflow(defn, {
            "prompt": "a warrior in medieval armor, fantasy art",
            "pose_image": "pose_001.png",
        })
        assert rendered is not None
        assert rendered["5"]["inputs"]["text"] == "a warrior in medieval armor, fantasy art"
        assert rendered["3"]["inputs"]["image"] == "pose_001.png"

    def test_controlnet_strength_substituted(self, workflow_manager):
        defn = self._get_defn(workflow_manager, "blender_depth_guided")
        rendered = workflow_manager.render_workflow(defn, {
            "prompt": "test",
            "depth_image": "d.png",
            "source_image": "s.png",
            "controlnet_strength": 0.7,
        })
        assert rendered["8"]["inputs"]["strength"] == 0.7

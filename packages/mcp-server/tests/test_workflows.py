"""Tests for workflow validation and parsing"""

import json
import pytest
from pathlib import Path
from managers.workflow_manager import WorkflowManager


@pytest.fixture
def workflow_manager():
    """Create a WorkflowManager with the actual workflows directory."""
    workflows_dir = Path(__file__).parent.parent / "workflows"
    return WorkflowManager(workflows_dir)


class TestWorkflowDiscovery:
    """Test workflow file discovery and parsing."""

    def test_workflows_directory_exists(self, workflow_manager):
        """Verify workflows directory exists."""
        assert workflow_manager.workflows_dir.exists()

    def test_workflows_discovered(self, workflow_manager):
        """Verify workflows are discovered."""
        assert len(workflow_manager.tool_definitions) > 0

    def test_core_workflows_present(self, workflow_manager):
        """Verify core workflows are present."""
        tool_names = [d.tool_name for d in workflow_manager.tool_definitions]

        # Core workflows that should always exist
        expected = ["generate_image", "generate_video", "generate_song"]
        for name in expected:
            assert name in tool_names, f"Missing core workflow: {name}"

    def test_workflow_has_required_params(self, workflow_manager):
        """Verify each workflow has at least one required parameter."""
        for defn in workflow_manager.tool_definitions:
            required = [p for p in defn.parameters.values() if p.required]
            assert len(required) > 0, f"Workflow {defn.tool_name} has no required parameters"


class TestWorkflowParameters:
    """Test workflow parameter extraction."""

    def test_generate_image_params(self, workflow_manager):
        """Verify generate_image has expected parameters."""
        defn = next((d for d in workflow_manager.tool_definitions if d.tool_name == "generate_image"), None)
        assert defn is not None

        param_names = list(defn.parameters.keys())
        assert "prompt" in param_names
        assert "width" in param_names
        assert "height" in param_names
        assert "steps" in param_names

        # prompt should be required
        assert defn.parameters["prompt"].required

    def test_generate_video_params(self, workflow_manager):
        """Verify generate_video has expected parameters."""
        defn = next((d for d in workflow_manager.tool_definitions if d.tool_name == "generate_video"), None)
        assert defn is not None

        param_names = list(defn.parameters.keys())
        assert "prompt" in param_names
        assert "frames" in param_names or "length" in param_names
        assert "fps" in param_names

    def test_generate_song_params(self, workflow_manager):
        """Verify generate_song has expected parameters."""
        defn = next((d for d in workflow_manager.tool_definitions if d.tool_name == "generate_song"), None)
        assert defn is not None

        param_names = list(defn.parameters.keys())
        assert "tags" in param_names
        assert "lyrics" in param_names

        # Both should be required
        assert defn.parameters["tags"].required
        assert defn.parameters["lyrics"].required


class TestWorkflowOutputTypes:
    """Test workflow output type detection."""

    def test_image_workflow_output(self, workflow_manager):
        """Verify image workflows output images."""
        defn = next((d for d in workflow_manager.tool_definitions if d.tool_name == "generate_image"), None)
        assert defn is not None
        assert "images" in defn.output_preferences or "image" in defn.output_preferences

    def test_video_workflow_output(self, workflow_manager):
        """Verify video workflows output videos."""
        defn = next((d for d in workflow_manager.tool_definitions if d.tool_name == "generate_video"), None)
        assert defn is not None
        assert "videos" in defn.output_preferences or "video" in defn.output_preferences

    def test_audio_workflow_output(self, workflow_manager):
        """Verify audio workflows output audio."""
        defn = next((d for d in workflow_manager.tool_definitions if d.tool_name == "generate_song"), None)
        assert defn is not None
        assert "audio" in defn.output_preferences or "audios" in defn.output_preferences


class TestWorkflowJSON:
    """Test raw workflow JSON files."""

    def test_all_workflow_files_valid_json(self):
        """Verify all workflow files are valid JSON."""
        workflows_dir = Path(__file__).parent.parent / "workflows"
        for json_file in workflows_dir.glob("*.json"):
            try:
                with open(json_file, "r") as f:
                    data = json.load(f)
                assert isinstance(data, dict), f"{json_file.name} root should be a dict"
            except json.JSONDecodeError as e:
                pytest.fail(f"{json_file.name} is not valid JSON: {e}")

    def test_workflow_nodes_have_class_type(self):
        """Verify all workflow nodes have class_type."""
        workflows_dir = Path(__file__).parent.parent / "workflows"
        for json_file in workflows_dir.glob("*.json"):
            with open(json_file, "r") as f:
                data = json.load(f)

            for node_id, node_data in data.items():
                if isinstance(node_data, dict) and "inputs" in node_data:
                    assert "class_type" in node_data, f"{json_file.name} node {node_id} missing class_type"

    def test_param_placeholders_valid(self):
        """Verify PARAM_* placeholders have valid formats."""
        workflows_dir = Path(__file__).parent.parent / "workflows"
        valid_prefixes = ["PARAM_", "PARAM_INT_", "PARAM_FLOAT_", "PARAM_STR_"]

        for json_file in workflows_dir.glob("*.json"):
            with open(json_file, "r") as f:
                content = f.read()

            # Find all PARAM_ strings
            import re
            params = re.findall(r'"(PARAM_[A-Z_]+)"', content)

            for param in params:
                valid = any(param.startswith(prefix) for prefix in valid_prefixes)
                assert valid, f"{json_file.name} has invalid parameter format: {param}"

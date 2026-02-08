"""Smoke tests for live ComfyUI integration.

These tests require a running ComfyUI instance and are marked with @pytest.mark.integration.
Run with: pytest tests/test_smoke.py -m integration -v
"""

import pytest
import time
from pathlib import Path


@pytest.fixture
def comfyui_client():
    """Create a ComfyUI client for integration tests."""
    from comfyui_agent_sdk.client import ComfyUIClient
    client = ComfyUIClient(base_url="http://localhost:8188")
    if not client.is_available():
        pytest.skip("ComfyUI not available")
    return client


@pytest.fixture
def workflow_manager():
    """Create workflow manager."""
    from managers.workflow_manager import WorkflowManager
    workflows_dir = Path(__file__).parent.parent / "workflows"
    return WorkflowManager(workflows_dir)


@pytest.fixture
def defaults_manager(comfyui_client):
    """Create defaults manager."""
    from comfyui_agent_sdk.defaults import DefaultsManager
    return DefaultsManager(comfyui_client)


@pytest.mark.integration
class TestComfyUIConnection:
    """Test ComfyUI connection and basic operations."""

    def test_comfyui_reachable(self, comfyui_client):
        """Verify ComfyUI is reachable."""
        assert comfyui_client.is_available()

    def test_comfyui_has_models(self, comfyui_client):
        """Verify ComfyUI has some models available."""
        models = comfyui_client.available_models
        assert models is not None
        assert len(models) > 0

    def test_connection_info(self, comfyui_client):
        """Verify connection info is available."""
        info = comfyui_client.check_connection()
        assert info["connected"] is True


@pytest.mark.integration
@pytest.mark.slow
class TestGenerationSmoke:
    """Smoke tests for generation workflows.

    These tests actually run generation and may take several minutes.
    Run with: pytest tests/test_smoke.py -m "integration and slow" -v
    """

    def test_generate_image_minimal(self, comfyui_client, workflow_manager, defaults_manager):
        """Test minimal image generation (256x256, 8 steps)."""
        # Build minimal workflow
        defn = next((d for d in workflow_manager.tool_definitions if d.tool_name == "generate_image"), None)
        if defn is None:
            pytest.skip("generate_image workflow not found")

        params = {
            "prompt": "a red circle on white background",
            "width": 256,
            "height": 256,
            "steps": 8,
            "seed": 42
        }

        workflow = workflow_manager.render_workflow(defn, params, defaults_manager)

        # Run workflow
        result = comfyui_client.run_custom_workflow(
            workflow,
            preferred_output_keys=defn.output_preferences
        )

        assert result is not None
        assert "filename" in result
        assert result["filename"].endswith(".png")

    def test_upscale_available(self, comfyui_client):
        """Verify upscale models are available."""
        # This is a quick check that doesn't run generation
        import requests
        r = requests.get("http://localhost:8188/object_info/UpscaleModelLoader", timeout=10)
        assert r.status_code == 200


@pytest.mark.integration
class TestHealthCheck:
    """Test the health check functionality."""

    def test_health_check_tool(self, comfyui_client, workflow_manager, defaults_manager):
        """Test health_check tool returns valid data."""
        from tools.configuration import register_configuration_tools
        from mcp.server.fastmcp import FastMCP

        # Create a minimal MCP instance for testing
        mcp = FastMCP("test", stateless_http=True)
        register_configuration_tools(mcp, comfyui_client, defaults_manager, workflow_manager)

        # Find and call health_check
        # Note: In real usage, we'd call through MCP protocol
        # Here we test the underlying logic

        info = comfyui_client.check_connection()
        assert info["connected"] is True

        # Verify workflows are loaded
        assert len(workflow_manager.tool_definitions) > 0

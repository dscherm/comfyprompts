"""Tests for error handling and robustness features"""

import pytest
from comfyui_agent_sdk.client import parse_comfyui_error


class TestErrorParser:
    """Test the ComfyUI error parser."""

    def test_vram_error_detection(self):
        """Test VRAM/OOM error detection."""
        error = {"message": "CUDA out of memory. Tried to allocate 2GB", "type": "runtime_error"}
        result = parse_comfyui_error(error)
        assert "VRAM" in result
        assert "lowvram" in result.lower()

    def test_vram_error_oom_keyword(self):
        """Test OOM keyword detection."""
        error = {"message": "OOM when allocating tensor", "type": "error"}
        result = parse_comfyui_error(error)
        assert "VRAM" in result

    def test_missing_model_error(self):
        """Test missing model error detection."""
        error = {"type": "value_not_in_list", "message": "Model xyz not found"}
        result = parse_comfyui_error(error)
        assert "model" in result.lower() or "missing" in result.lower()

    def test_missing_node_error(self):
        """Test missing node error detection."""
        error = {"message": "Missing node ComfyUI-AnimateDiff", "type": "missing_node"}
        result = parse_comfyui_error(error)
        assert "node" in result.lower()
        assert "install" in result.lower()

    def test_connection_error(self):
        """Test connection error detection."""
        error = {"message": "Connection refused to localhost:8188", "type": "network"}
        result = parse_comfyui_error(error)
        assert "connection" in result.lower()

    def test_timeout_error(self):
        """Test timeout error detection."""
        error = {"message": "Request timeout after 30s", "type": "timeout"}
        result = parse_comfyui_error(error)
        assert "timeout" in result.lower()

    def test_unknown_error_passthrough(self):
        """Test that unknown errors pass through message."""
        error = {"message": "Some unknown error occurred", "type": "unknown"}
        result = parse_comfyui_error(error)
        assert "unknown error" in result.lower()

    def test_empty_error(self):
        """Test handling of empty error dict."""
        result = parse_comfyui_error({})
        assert result  # Should return something, not crash

    def test_non_dict_error(self):
        """Test handling of non-dict error."""
        result = parse_comfyui_error("string error")
        assert result == "string error"


class TestComfyUIClientRobustness:
    """Test ComfyUI client robustness features."""

    def test_client_import(self):
        """Test that ComfyUIClient can be imported."""
        from comfyui_agent_sdk.client import ComfyUIClient
        assert ComfyUIClient is not None

    def test_client_has_health_methods(self):
        """Test that client has health check methods."""
        from comfyui_agent_sdk.client import ComfyUIClient
        client = ComfyUIClient(base_url="http://localhost:8188")
        assert hasattr(client, "is_available")
        assert hasattr(client, "check_connection")

    @pytest.mark.integration
    def test_health_check_returns_dict(self):
        """Test health check returns properly structured dict."""
        from comfyui_agent_sdk.client import ComfyUIClient
        client = ComfyUIClient(base_url="http://localhost:8188")
        result = client.check_connection()
        assert isinstance(result, dict)
        assert "connected" in result

    @pytest.mark.integration
    def test_is_available_returns_bool(self):
        """Test is_available returns boolean."""
        from comfyui_agent_sdk.client import ComfyUIClient
        client = ComfyUIClient(base_url="http://localhost:8188")
        result = client.is_available()
        assert isinstance(result, bool)

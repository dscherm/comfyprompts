"""Pytest configuration and fixtures"""

import pytest
from comfyui_agent_sdk.assets import AssetRegistry


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: marks tests as integration tests (require ComfyUI)")
    config.addinivalue_line("markers", "slow: marks tests as slow (may take minutes)")


@pytest.fixture
def asset_registry():
    """Create a fresh AssetRegistry for each test."""
    return AssetRegistry(comfyui_base_url="http://localhost:8188", ttl_hours=24)


@pytest.fixture
def sample_asset_data():
    """Sample asset data for testing."""
    return {
        "filename": "test.png",
        "subfolder": "",
        "folder_type": "output",
        "workflow_id": "generate_image",
        "prompt_id": "test_prompt_123",
        "mime_type": "image/png",
        "width": 512,
        "height": 512,
        "bytes_size": 12345,
        "comfy_history": {"test": "data"},
        "submitted_workflow": {"nodes": []},
        "metadata": {"test": "metadata"}
    }

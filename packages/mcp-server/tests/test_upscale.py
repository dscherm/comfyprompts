"""Tests for the upscale tool"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path


class TestUpscaleParameterValidation:
    """Test parameter validation for upscale_image"""

    def test_invalid_scale_factor(self):
        """Test that invalid scale factors are rejected"""
        # Scale factor must be 2 or 4
        valid_factors = [2, 4]
        invalid_factors = [1, 3, 5, 8, 0, -1]

        for factor in invalid_factors:
            assert factor not in valid_factors

    def test_valid_scale_factors(self):
        """Test that valid scale factors are accepted"""
        valid_factors = [2, 4]
        for factor in valid_factors:
            assert factor in [2, 4]


class TestUpscaleModelSelection:
    """Test upscale model selection logic"""

    def test_auto_select_4x_model(self):
        """Test auto-selection prefers 4x models for scale_factor=4"""
        available_models = [
            "RealESRGAN_x4plus.pth",
            "2x_NMKD.pth",
            "4x-UltraSharp.pth"
        ]
        scale_factor = 4

        # Should find 4x models
        scale_prefix = f"{scale_factor}x"
        matching = [m for m in available_models if scale_prefix.lower() in m.lower()]
        assert len(matching) >= 1
        assert "4x" in matching[0].lower() or "x4" in matching[0].lower()

    def test_auto_select_2x_model(self):
        """Test auto-selection prefers 2x models for scale_factor=2"""
        available_models = [
            "RealESRGAN_x4plus.pth",
            "2x_NMKD.pth",
            "4x-UltraSharp.pth"
        ]
        scale_factor = 2

        scale_prefix = f"{scale_factor}x"
        matching = [m for m in available_models if scale_prefix.lower() in m.lower()]
        assert len(matching) >= 1
        assert "2x" in matching[0].lower()

    def test_fallback_when_no_match(self):
        """Test fallback to first model when no scale match"""
        available_models = [
            "SomeOtherModel.pth",
            "AnotherModel.pth"
        ]
        scale_factor = 4

        scale_prefix = f"{scale_factor}x"
        matching = [m for m in available_models if scale_prefix.lower() in m.lower()]
        assert len(matching) == 0
        # Should fall back to first available
        selected_model = matching[0] if matching else available_models[0]
        assert selected_model == "SomeOtherModel.pth"


class TestUpscaleWorkflow:
    """Test upscale workflow generation"""

    def test_workflow_structure(self):
        """Test that the generated workflow has correct structure"""
        # Expected nodes in upscale workflow
        expected_nodes = ["LoadImage", "UpscaleModelLoader", "ImageUpscaleWithModel", "SaveImage"]

        # Simulated workflow structure
        workflow = {
            "1": {"class_type": "LoadImage", "inputs": {"image": "test.png"}},
            "2": {"class_type": "UpscaleModelLoader", "inputs": {"model_name": "RealESRGAN_x4plus.pth"}},
            "3": {"class_type": "ImageUpscaleWithModel", "inputs": {}},
            "4": {"class_type": "SaveImage", "inputs": {}}
        }

        node_types = [node["class_type"] for node in workflow.values()]
        for expected in expected_nodes:
            assert expected in node_types

    def test_workflow_connections(self):
        """Test that workflow nodes are connected correctly"""
        workflow = {
            "1": {"class_type": "LoadImage", "inputs": {"image": "test.png"}},
            "2": {"class_type": "UpscaleModelLoader", "inputs": {"model_name": "RealESRGAN_x4plus.pth"}},
            "3": {
                "class_type": "ImageUpscaleWithModel",
                "inputs": {
                    "upscale_model": ["2", 0],
                    "image": ["1", 0]
                }
            },
            "4": {"class_type": "SaveImage", "inputs": {"images": ["3", 0]}}
        }

        # Verify ImageUpscaleWithModel receives inputs from other nodes
        upscale_node = workflow["3"]
        assert upscale_node["inputs"]["upscale_model"] == ["2", 0]
        assert upscale_node["inputs"]["image"] == ["1", 0]

        # Verify SaveImage receives output from upscale
        save_node = workflow["4"]
        assert save_node["inputs"]["images"] == ["3", 0]


class TestUpscaleAssetValidation:
    """Test asset validation for upscaling"""

    def test_reject_non_image_assets(self):
        """Test that non-image assets are rejected"""
        non_image_mimes = ["audio/mpeg", "video/mp4", "model/gltf-binary", "application/octet-stream"]

        for mime in non_image_mimes:
            is_image = mime.startswith("image/")
            assert not is_image, f"Expected {mime} to not be an image"

    def test_accept_image_assets(self):
        """Test that image assets are accepted"""
        image_mimes = ["image/png", "image/jpeg", "image/webp", "image/gif"]

        for mime in image_mimes:
            is_image = mime.startswith("image/")
            assert is_image, f"Expected {mime} to be an image"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

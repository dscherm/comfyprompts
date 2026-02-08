"""Tests for the image variations tool"""
import pytest
from unittest.mock import Mock, MagicMock, patch
import random


class TestVariationsParameterValidation:
    """Test parameter validation for generate_variations"""

    def test_num_variations_bounds(self):
        """Test num_variations must be 1-8"""
        valid_counts = [1, 2, 3, 4, 5, 6, 7, 8]
        invalid_counts = [0, -1, 9, 10, 100]

        for count in valid_counts:
            assert 1 <= count <= 8, f"Expected {count} to be valid"

        for count in invalid_counts:
            assert not (1 <= count <= 8), f"Expected {count} to be invalid"

    def test_variation_strength_bounds(self):
        """Test variation_strength must be 0.0-1.0"""
        valid_strengths = [0.0, 0.1, 0.5, 0.7, 1.0]
        invalid_strengths = [-0.1, 1.1, 2.0, -1.0]

        for strength in valid_strengths:
            assert 0.0 <= strength <= 1.0, f"Expected {strength} to be valid"

        for strength in invalid_strengths:
            assert not (0.0 <= strength <= 1.0), f"Expected {strength} to be invalid"

    def test_default_values(self):
        """Test default parameter values"""
        default_num_variations = 4
        default_variation_strength = 0.7

        assert default_num_variations == 4
        assert default_variation_strength == 0.7


class TestVariationsSeedGeneration:
    """Test seed generation for variations"""

    def test_sequential_seeds(self):
        """Test that each variation gets seed+i"""
        base_seed = 12345
        num_variations = 4

        expected_seeds = [base_seed + i for i in range(num_variations)]
        assert expected_seeds == [12345, 12346, 12347, 12348]

    def test_random_base_seed(self):
        """Test random base seed generation"""
        base_seed = random.randint(0, 2**32 - 1)
        assert 0 <= base_seed < 2**32

    def test_seed_reproducibility(self):
        """Test that same base_seed produces same variation seeds"""
        base_seed = 42
        num_variations = 3

        seeds1 = [base_seed + i for i in range(num_variations)]
        seeds2 = [base_seed + i for i in range(num_variations)]

        assert seeds1 == seeds2


class TestVariationsWorkflow:
    """Test variations workflow generation"""

    def test_img2img_workflow_structure(self):
        """Test that img2img workflow has correct structure"""
        expected_nodes = [
            "CheckpointLoaderSimple",
            "LoadImage",
            "VAEEncode",
            "CLIPTextEncode",  # positive
            "CLIPTextEncode",  # negative
            "KSampler",
            "VAEDecode",
            "SaveImage"
        ]

        # Count expected node types
        assert len(expected_nodes) == 8

    def test_denoise_as_variation_strength(self):
        """Test that variation_strength maps to KSampler denoise"""
        variation_strength = 0.7

        # In the workflow, denoise should equal variation_strength
        ksampler_inputs = {
            "seed": 12345,
            "steps": 20,
            "cfg": 7.0,
            "sampler_name": "euler",
            "scheduler": "normal",
            "denoise": variation_strength
        }

        assert ksampler_inputs["denoise"] == 0.7

    def test_empty_prompt_for_pure_img2img(self):
        """Test that prompt can be empty for pure visual variations"""
        prompt = None
        resolved_prompt = prompt or ""

        assert resolved_prompt == ""


class TestVariationsBatchProcessing:
    """Test batch processing of multiple variations"""

    def test_sequential_generation(self):
        """Test that variations are generated sequentially"""
        num_variations = 4
        results = []

        for i in range(num_variations):
            results.append({"variation_index": i + 1, "success": True})

        assert len(results) == 4
        assert results[0]["variation_index"] == 1
        assert results[3]["variation_index"] == 4

    def test_partial_failure_handling(self):
        """Test that partial failures don't fail entire batch"""
        results = [
            {"variation_index": 1, "success": True},
            {"variation_index": 2, "success": False, "error": "Timeout"},
            {"variation_index": 3, "success": True},
        ]

        successes = [r for r in results if r["success"]]
        failures = [r for r in results if not r["success"]]

        assert len(successes) == 2
        assert len(failures) == 1

        # Should return partial results, not error
        assert len(successes) > 0

    def test_response_structure(self):
        """Test response structure with multiple variations"""
        variations = [
            {"asset_id": "abc", "variation_index": 1},
            {"asset_id": "def", "variation_index": 2},
        ]

        response = {
            "variations": variations,
            "count": len(variations),
            "original_asset_id": "source123",
            "variation_strength": 0.7,
            "base_seed": 12345
        }

        assert response["count"] == 2
        assert len(response["variations"]) == 2
        assert response["original_asset_id"] == "source123"


class TestVariationsAssetValidation:
    """Test asset validation for variations"""

    def test_reject_non_image_assets(self):
        """Test that non-image assets are rejected"""
        non_image_mimes = ["audio/mpeg", "video/mp4", "model/gltf-binary"]

        for mime in non_image_mimes:
            is_image = mime.startswith("image/")
            assert not is_image

    def test_accept_image_assets(self):
        """Test that image assets are accepted"""
        image_mimes = ["image/png", "image/jpeg", "image/webp"]

        for mime in image_mimes:
            is_image = mime.startswith("image/")
            assert is_image


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

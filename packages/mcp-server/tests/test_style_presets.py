"""Tests for style presets functionality"""

import pytest
from managers.style_presets_manager import StylePresetsManager


@pytest.fixture
def presets_manager():
    """Create a fresh StylePresetsManager for each test."""
    return StylePresetsManager()


class TestBuiltinPresets:
    """Test built-in style presets"""

    def test_list_presets_returns_list(self, presets_manager):
        """Verify list_presets returns a list of presets."""
        presets = presets_manager.list_presets()
        assert isinstance(presets, list)
        assert len(presets) > 0

    def test_builtin_presets_exist(self, presets_manager):
        """Verify expected built-in presets are available."""
        preset_ids = [p["id"] for p in presets_manager.list_presets()]
        expected = ["photorealistic", "anime", "ghibli", "pixel_art", "cyberpunk", "fantasy"]
        for expected_id in expected:
            assert expected_id in preset_ids, f"Missing preset: {expected_id}"

    def test_get_preset_returns_details(self, presets_manager):
        """Verify get_preset returns full preset details."""
        preset = presets_manager.get_preset("anime")
        assert preset is not None
        assert "name" in preset
        assert "description" in preset
        assert "prompt_prefix" in preset
        assert "prompt_suffix" in preset

    def test_get_nonexistent_preset(self, presets_manager):
        """Verify get_preset returns None for unknown presets."""
        preset = presets_manager.get_preset("nonexistent_preset_xyz")
        assert preset is None


class TestApplyPreset:
    """Test applying presets to prompts"""

    def test_apply_preset_enhances_prompt(self, presets_manager):
        """Verify apply_preset adds prefix and suffix to prompt."""
        result = presets_manager.apply_preset("anime", "a girl with blue hair")

        assert "enhanced_prompt" in result
        assert "anime" in result["enhanced_prompt"].lower()
        assert "a girl with blue hair" in result["enhanced_prompt"]

    def test_apply_preset_includes_negative(self, presets_manager):
        """Verify apply_preset includes negative prompt."""
        result = presets_manager.apply_preset("photorealistic", "a sunset")

        assert "negative_prompt" in result
        assert len(result["negative_prompt"]) > 0

    def test_apply_preset_includes_settings(self, presets_manager):
        """Verify apply_preset includes recommended settings."""
        result = presets_manager.apply_preset("cinematic", "a hero")

        assert "settings" in result
        # Settings should contain common generation parameters
        assert isinstance(result["settings"], dict)

    def test_apply_preset_with_overrides(self, presets_manager):
        """Verify settings can be overridden when applying preset."""
        result = presets_manager.apply_preset(
            "anime",
            "a robot",
            {"steps": 50, "cfg": 2.0}
        )

        assert result["settings"]["steps"] == 50
        assert result["settings"]["cfg"] == 2.0

    def test_apply_nonexistent_preset_raises(self, presets_manager):
        """Verify applying nonexistent preset raises ValueError."""
        with pytest.raises(ValueError):
            presets_manager.apply_preset("nonexistent_xyz", "test prompt")


class TestPresetMetadata:
    """Test preset metadata and structure"""

    def test_preset_has_type(self, presets_manager):
        """Verify presets have type field (builtin or custom)."""
        presets = presets_manager.list_presets()
        for preset in presets:
            assert "type" in preset
            assert preset["type"] in ("builtin", "custom")

    def test_ghibli_suggests_lora(self, presets_manager):
        """Verify ghibli preset suggests appropriate LoRA."""
        preset = presets_manager.get_preset("ghibli")
        assert "suggested_lora" in preset

    def test_pixel_art_suggests_lora(self, presets_manager):
        """Verify pixel_art preset suggests appropriate LoRA."""
        preset = presets_manager.get_preset("pixel_art")
        assert "suggested_lora" in preset


class TestCustomPresets:
    """Test custom preset creation and deletion"""

    def test_create_custom_preset(self, presets_manager):
        """Verify custom presets can be created."""
        result = presets_manager.create_custom_preset(
            preset_id="test_custom",
            name="Test Custom Style",
            description="A test custom style",
            prompt_prefix="test style, ",
            prompt_suffix=", test quality",
            negative_prompt="bad test"
        )

        assert result["success"] is True
        assert result["preset_id"] == "test_custom"

        # Clean up
        presets_manager.delete_custom_preset("test_custom")

    def test_cannot_override_builtin(self, presets_manager):
        """Verify built-in presets cannot be overridden."""
        with pytest.raises(ValueError):
            presets_manager.create_custom_preset(
                preset_id="anime",  # builtin preset
                name="Override Attempt",
                description="Should fail"
            )

    def test_delete_custom_preset(self, presets_manager):
        """Verify custom presets can be deleted."""
        # Create first
        presets_manager.create_custom_preset(
            preset_id="to_delete",
            name="To Delete",
            description="Will be deleted"
        )

        # Verify it exists
        assert presets_manager.get_preset("to_delete") is not None

        # Delete
        result = presets_manager.delete_custom_preset("to_delete")
        assert result["success"] is True

        # Verify it's gone
        assert presets_manager.get_preset("to_delete") is None

    def test_cannot_delete_builtin(self, presets_manager):
        """Verify built-in presets cannot be deleted."""
        with pytest.raises(ValueError):
            presets_manager.delete_custom_preset("anime")

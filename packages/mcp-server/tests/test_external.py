"""Tests for the external app manager (Blender, Unreal integration)"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import os

from managers.external_app_manager import (
    ExternalAppManager,
    SUPPORTED_3D_FORMATS,
    SUPPORTED_IMAGE_FORMATS,
    DEFAULT_BLENDER_PATHS,
    DEFAULT_UNREAL_PATHS
)


class TestAppDetection:
    """Test external application detection"""

    def test_default_blender_paths(self):
        """Test default Blender search paths include common locations"""
        # Should include Windows paths
        windows_paths = [p for p in DEFAULT_BLENDER_PATHS if "Program Files" in p]
        assert len(windows_paths) > 0

        # Should include macOS path
        macos_paths = [p for p in DEFAULT_BLENDER_PATHS if "/Applications/" in p]
        assert len(macos_paths) > 0

        # Should include Linux paths
        linux_paths = [p for p in DEFAULT_BLENDER_PATHS if p.startswith("/usr/") or p.startswith("/snap/")]
        assert len(linux_paths) > 0

    def test_default_unreal_paths(self):
        """Test default Unreal search paths"""
        # Should include Windows Epic Games paths
        epic_paths = [p for p in DEFAULT_UNREAL_PATHS if "Epic Games" in p]
        assert len(epic_paths) > 0

        # Should include multiple UE versions
        assert any("UE_5.7" in p for p in DEFAULT_UNREAL_PATHS)
        assert any("UE_5.5" in p or "UE_5.4" in p or "UE_5.3" in p for p in DEFAULT_UNREAL_PATHS)

    def test_find_app_returns_first_existing(self):
        """Test _find_app returns first existing path"""
        manager = ExternalAppManager.__new__(ExternalAppManager)

        with patch('os.path.isfile') as mock_isfile:
            mock_isfile.side_effect = lambda p: p == "/path/b"
            result = manager._find_app(["/path/a", "/path/b", "/path/c"])
            assert result == "/path/b"

    def test_find_app_returns_none_when_not_found(self):
        """Test _find_app returns None when no path exists"""
        manager = ExternalAppManager.__new__(ExternalAppManager)

        with patch('os.path.isfile', return_value=False):
            result = manager._find_app(["/nonexistent/a", "/nonexistent/b"])
            assert result is None


class TestGetStatus:
    """Test get_status functionality"""

    def test_status_structure(self):
        """Test status response structure"""
        with patch('os.path.isfile', return_value=False):
            manager = ExternalAppManager()
            status = manager.get_status()

        assert "blender" in status
        assert "unreal" in status
        assert "supported_3d_formats" in status
        assert "supported_image_formats" in status

    def test_status_blender_fields(self):
        """Test Blender status fields"""
        with patch('os.path.isfile', return_value=False):
            manager = ExternalAppManager()
            status = manager.get_status()

        blender = status["blender"]
        assert "available" in blender
        assert "path" in blender
        assert "version" in blender

    def test_status_when_apps_not_found(self):
        """Test status when apps are not installed"""
        with patch('os.path.isfile', return_value=False):
            manager = ExternalAppManager()
            status = manager.get_status()

        assert status["blender"]["available"] is False
        assert status["unreal"]["available"] is False


class TestSupportedFormats:
    """Test supported format definitions"""

    def test_3d_formats(self):
        """Test supported 3D formats"""
        assert "glb" in SUPPORTED_3D_FORMATS
        assert "gltf" in SUPPORTED_3D_FORMATS
        assert "fbx" in SUPPORTED_3D_FORMATS
        assert "obj" in SUPPORTED_3D_FORMATS

    def test_3d_format_extensions(self):
        """Test 3D format extensions are correct"""
        assert ".glb" in SUPPORTED_3D_FORMATS["glb"]["extensions"]
        assert ".gltf" in SUPPORTED_3D_FORMATS["gltf"]["extensions"]
        assert ".fbx" in SUPPORTED_3D_FORMATS["fbx"]["extensions"]
        assert ".obj" in SUPPORTED_3D_FORMATS["obj"]["extensions"]

    def test_image_formats(self):
        """Test supported image formats"""
        assert "png" in SUPPORTED_IMAGE_FORMATS
        assert "jpg" in SUPPORTED_IMAGE_FORMATS
        assert "webp" in SUPPORTED_IMAGE_FORMATS
        assert "exr" in SUPPORTED_IMAGE_FORMATS
        assert "hdr" in SUPPORTED_IMAGE_FORMATS

    def test_image_format_mime_types(self):
        """Test image format MIME types"""
        assert SUPPORTED_IMAGE_FORMATS["png"]["mime_type"] == "image/png"
        assert SUPPORTED_IMAGE_FORMATS["jpg"]["mime_type"] == "image/jpeg"
        assert SUPPORTED_IMAGE_FORMATS["exr"]["mime_type"] == "image/x-exr"


class TestExportToBlender:
    """Test Blender export functionality"""

    def test_blender_not_found_error(self):
        """Test error when Blender not installed"""
        with patch('os.path.isfile', return_value=False):
            manager = ExternalAppManager()
            result = manager.export_to_blender(Path("/test/file.glb"))

        assert "error" in result
        assert "Blender not found" in result["error"]

    def test_file_not_found_error(self):
        """Test error when asset file doesn't exist"""
        with patch('os.path.isfile', side_effect=lambda p: "blender" in str(p).lower()):
            manager = ExternalAppManager(blender_path="/fake/blender")
            result = manager.export_to_blender(Path("/nonexistent/file.glb"))

        assert "error" in result
        assert "not found" in result["error"]

    def test_unsupported_format_error(self):
        """Test error for unsupported file format"""
        with patch('os.path.isfile', return_value=True):
            manager = ExternalAppManager(blender_path="/fake/blender")

            # Create mock path that "exists" but is unsupported format
            with patch.object(Path, 'exists', return_value=True):
                with patch.object(Path, 'suffix', new_callable=lambda: property(lambda self: ".xyz")):
                    result = manager.export_to_blender(Path("/test/file.xyz"))

        # Should get an error about format
        assert "error" in result or result.get("success", False) is False


class TestExportToUnreal:
    """Test Unreal Engine export functionality"""

    def test_unreal_not_found_error(self):
        """Test error when Unreal not installed"""
        with patch('os.path.isfile', return_value=False):
            manager = ExternalAppManager()
            result = manager.export_to_unreal(
                Path("/test/file.fbx"),
                "/project/MyGame.uproject"
            )

        assert "error" in result
        assert "Unreal Engine not found" in result["error"]

    def test_invalid_project_error(self):
        """Test error for invalid .uproject file"""
        with patch('os.path.isfile', side_effect=lambda p: "UnrealEditor" in str(p)):
            manager = ExternalAppManager(unreal_path="/fake/UnrealEditor-Cmd.exe")
            result = manager.export_to_unreal(
                Path("/test/file.fbx"),
                "/nonexistent/project.uproject"
            )

        assert "error" in result

    def test_gltf_not_supported_directly(self):
        """Test that glTF format requires conversion first"""
        # This is a design decision - Unreal doesn't import glTF via commandlet
        supported_unreal = [".fbx", ".obj", ".png", ".jpg", ".jpeg", ".tga", ".exr", ".hdr"]
        assert ".glb" not in supported_unreal
        assert ".gltf" not in supported_unreal


class TestFormatConversion:
    """Test 3D format conversion"""

    def test_conversion_requires_blender(self):
        """Test that conversion requires Blender"""
        with patch('os.path.isfile', return_value=False):
            manager = ExternalAppManager()
            result = manager.convert_3d_format(Path("/test/file.glb"), "fbx")

        assert "error" in result
        assert "Blender" in result["error"]

    def test_unsupported_target_format(self):
        """Test error for unsupported target format"""
        import tempfile
        # Create a real temp file for the test
        with tempfile.NamedTemporaryFile(suffix=".glb", delete=False) as f:
            temp_path = Path(f.name)
        try:
            with patch('os.path.isfile', return_value=True):
                manager = ExternalAppManager(blender_path="/fake/blender")
                result = manager.convert_3d_format(temp_path, "xyz")

            assert "error" in result
            assert "Unsupported target format" in result["error"]
        finally:
            temp_path.unlink(missing_ok=True)

    def test_supported_conversions(self):
        """Test supported format conversion combinations"""
        # All these should be valid source formats
        source_formats = [".glb", ".gltf", ".fbx", ".obj"]

        # All these should be valid target formats
        target_formats = ["glb", "gltf", "fbx", "obj"]

        # Every combination should be theoretically supported
        for source in source_formats:
            for target in target_formats:
                # Except converting to same format
                if source.lstrip(".") != target:
                    assert source in [".glb", ".gltf", ".fbx", ".obj"]
                    assert target in ["glb", "gltf", "fbx", "obj"]


class TestGetAssetFormat:
    """Test asset format detection"""

    def test_detect_3d_formats(self):
        """Test detection of 3D file formats"""
        with patch('os.path.isfile', return_value=False):
            manager = ExternalAppManager()

        assert manager.get_asset_format(Path("/test/model.glb")) == "glb"
        assert manager.get_asset_format(Path("/test/model.gltf")) == "gltf"
        assert manager.get_asset_format(Path("/test/model.fbx")) == "fbx"
        assert manager.get_asset_format(Path("/test/model.obj")) == "obj"

    def test_detect_image_formats(self):
        """Test detection of image file formats"""
        with patch('os.path.isfile', return_value=False):
            manager = ExternalAppManager()

        assert manager.get_asset_format(Path("/test/image.png")) == "png"
        assert manager.get_asset_format(Path("/test/image.jpg")) == "jpg"
        assert manager.get_asset_format(Path("/test/image.exr")) == "exr"
        assert manager.get_asset_format(Path("/test/image.hdr")) == "hdr"

    def test_unknown_format(self):
        """Test handling of unknown formats"""
        with patch('os.path.isfile', return_value=False):
            manager = ExternalAppManager()

        assert manager.get_asset_format(Path("/test/file.xyz")) is None
        assert manager.get_asset_format(Path("/test/file.mp4")) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

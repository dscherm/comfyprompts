# thumbnail_generator.py - Generate preview thumbnails for outputs

import os
from pathlib import Path
from typing import Optional, Tuple
import base64
import io

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("Warning: Pillow not installed. Install with: pip install Pillow")


class ThumbnailGenerator:
    """Generate preview thumbnails for various output types"""

    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or Path.home() / ".comfyui-prompter" / "thumbnails"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_size = (256, 256)

    def get_thumbnail(self, file_path: str, size: Tuple[int, int] = None) -> Optional[str]:
        """
        Get or generate a thumbnail for a file

        Args:
            file_path: Path to the file
            size: Thumbnail size (width, height)

        Returns:
            Base64-encoded thumbnail image or None if failed
        """
        if not HAS_PIL:
            return None

        size = size or self.default_size
        path = Path(file_path)

        if not path.exists():
            return None

        # Check cache first
        cache_key = self._get_cache_key(file_path, size)
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Generate based on file type
        ext = path.suffix.lower()

        if ext in ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif']:
            thumbnail = self._generate_image_thumbnail(path, size)
        elif ext in ['.glb', '.gltf']:
            thumbnail = self._generate_3d_thumbnail(path, size)
        elif ext in ['.mp4', '.webm', '.mov', '.avi']:
            thumbnail = self._generate_video_thumbnail(path, size)
        else:
            return None

        # Cache the result
        if thumbnail:
            self._save_cached(cache_key, thumbnail)

        return thumbnail

    def _generate_image_thumbnail(self, path: Path, size: Tuple[int, int]) -> Optional[str]:
        """Generate thumbnail for an image file"""
        try:
            with Image.open(path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')

                # Create thumbnail preserving aspect ratio
                img.thumbnail(size, Image.Resampling.LANCZOS)

                # Save to bytes
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=85)
                buffer.seek(0)

                return base64.b64encode(buffer.getvalue()).decode('utf-8')
        except Exception as e:
            print(f"Error generating image thumbnail: {e}")
            return None

    def _generate_3d_thumbnail(self, path: Path, size: Tuple[int, int]) -> Optional[str]:
        """
        Generate thumbnail for a 3D model

        Note: This requires additional libraries like trimesh and pyrender
        For now, returns a placeholder or tries to find an existing preview
        """
        # Try to find an existing preview image (some workflows save these)
        preview_extensions = ['.png', '.jpg', '_preview.png', '_preview.jpg']
        for ext in preview_extensions:
            preview_path = path.with_suffix(ext)
            if preview_path.exists():
                return self._generate_image_thumbnail(preview_path, size)

        # Try without _preview suffix
        base_name = path.stem
        parent = path.parent
        for ext in ['.png', '.jpg']:
            preview_path = parent / f"{base_name}{ext}"
            if preview_path.exists():
                return self._generate_image_thumbnail(preview_path, size)

        # Check for renders in same folder
        for img_file in parent.glob(f"{base_name}*.png"):
            return self._generate_image_thumbnail(img_file, size)
        for img_file in parent.glob(f"{base_name}*.jpg"):
            return self._generate_image_thumbnail(img_file, size)

        # Return placeholder (a simple 3D icon)
        return self._generate_placeholder_3d(size)

    def _generate_video_thumbnail(self, path: Path, size: Tuple[int, int]) -> Optional[str]:
        """
        Generate thumbnail for a video file

        Extracts the first frame using cv2 if available
        """
        try:
            import cv2
            cap = cv2.VideoCapture(str(path))
            ret, frame = cap.read()
            cap.release()

            if ret:
                # Convert BGR to RGB
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame)
                img.thumbnail(size, Image.Resampling.LANCZOS)

                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=85)
                buffer.seek(0)

                return base64.b64encode(buffer.getvalue()).decode('utf-8')
        except ImportError:
            pass
        except Exception as e:
            print(f"Error generating video thumbnail: {e}")

        return self._generate_placeholder_video(size)

    def _generate_placeholder_3d(self, size: Tuple[int, int]) -> Optional[str]:
        """Generate a placeholder image for 3D models"""
        try:
            # Create a simple placeholder with "3D" text
            img = Image.new('RGB', size, color=(60, 60, 80))

            # Try to add text if we have a font
            try:
                from PIL import ImageDraw, ImageFont
                draw = ImageDraw.Draw(img)
                text = "3D"
                # Use default font
                font = ImageFont.load_default()
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                x = (size[0] - text_width) // 2
                y = (size[1] - text_height) // 2
                draw.text((x, y), text, fill=(200, 200, 220), font=font)
            except:
                pass

            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            buffer.seek(0)

            return base64.b64encode(buffer.getvalue()).decode('utf-8')
        except:
            return None

    def _generate_placeholder_video(self, size: Tuple[int, int]) -> Optional[str]:
        """Generate a placeholder image for videos"""
        try:
            img = Image.new('RGB', size, color=(40, 60, 80))

            try:
                from PIL import ImageDraw
                draw = ImageDraw.Draw(img)
                # Draw a play button triangle
                cx, cy = size[0] // 2, size[1] // 2
                triangle = [
                    (cx - 20, cy - 30),
                    (cx - 20, cy + 30),
                    (cx + 30, cy)
                ]
                draw.polygon(triangle, fill=(200, 200, 220))
            except:
                pass

            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            buffer.seek(0)

            return base64.b64encode(buffer.getvalue()).decode('utf-8')
        except:
            return None

    def _get_cache_key(self, file_path: str, size: Tuple[int, int]) -> str:
        """Generate a cache key for a file"""
        import hashlib
        path = Path(file_path)
        stat = path.stat()
        key_data = f"{file_path}_{stat.st_mtime}_{size[0]}x{size[1]}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _get_cached(self, cache_key: str) -> Optional[str]:
        """Get cached thumbnail"""
        cache_path = self.cache_dir / f"{cache_key}.txt"
        if cache_path.exists():
            try:
                return cache_path.read_text()
            except:
                pass
        return None

    def _save_cached(self, cache_key: str, data: str):
        """Save thumbnail to cache"""
        cache_path = self.cache_dir / f"{cache_key}.txt"
        try:
            cache_path.write_text(data)
        except:
            pass

    def clear_cache(self):
        """Clear thumbnail cache"""
        import shutil
        try:
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except:
            pass


# Singleton instance
_thumbnail_generator = None


def get_thumbnail_generator() -> ThumbnailGenerator:
    """Get the singleton thumbnail generator"""
    global _thumbnail_generator
    if _thumbnail_generator is None:
        _thumbnail_generator = ThumbnailGenerator()
    return _thumbnail_generator

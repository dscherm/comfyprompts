"""Image metadata extraction, preview encoding, and thumbnail generation."""

import base64
import logging
import os
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Optional, Union

import requests

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageOps

    _PIL = True
except ImportError:
    _PIL = False


# Simple in-memory cache for previews
_preview_cache: dict[str, "EncodedImage"] = {}


@dataclass(frozen=True)
class EncodedImage:
    """Encoded image result with metrics."""

    b64: str
    mime_type: str
    size_px: tuple[int, int]
    bytes_len: int
    b64_chars: int
    raw_bytes: bytes


# ------------------------------------------------------------------
# Public helpers
# ------------------------------------------------------------------


def fetch_asset_bytes(asset_url: str, timeout: int = 30) -> bytes:
    r = requests.get(asset_url, timeout=timeout)
    r.raise_for_status()
    return r.content


def get_image_metadata(image_bytes: bytes) -> dict[str, Any]:
    if not _PIL:
        return {"width": None, "height": None, "format": None}
    try:
        with Image.open(BytesIO(image_bytes)) as img:
            return {"width": img.width, "height": img.height, "format": img.format}
    except Exception:
        return {"width": None, "height": None, "format": None}


def create_thumbnail(
    image_bytes: bytes,
    max_dim: int = 512,
    quality: int = 75,
    fmt: str = "JPEG",
) -> bytes:
    if not _PIL:
        raise ImportError("Pillow is required")
    with Image.open(BytesIO(image_bytes)) as img:
        if img.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            bg.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")

        w, h = img.size
        if w > max_dim or h > max_dim:
            if w > h:
                nw, nh = max_dim, int(h * max_dim / w)
            else:
                nh, nw = max_dim, int(w * max_dim / h)
            img = img.resize((nw, nh), Image.Resampling.LANCZOS)

        buf = BytesIO()
        img.save(buf, format=fmt, quality=quality, optimize=True)
        return buf.getvalue()


def strip_image_metadata(image_bytes: bytes) -> bytes:
    if not _PIL:
        return image_bytes
    try:
        with Image.open(BytesIO(image_bytes)) as img:
            data = list(img.getdata())
            clean = Image.new(img.mode, img.size)
            clean.putdata(data)
            buf = BytesIO()
            out_fmt = img.format or "JPEG"
            if out_fmt == "PNG":
                clean.save(buf, format="PNG", optimize=True)
            else:
                clean.save(buf, format="JPEG", quality=95, optimize=True)
            return buf.getvalue()
    except Exception:
        return image_bytes


# ------------------------------------------------------------------
# MCP preview encoding
# ------------------------------------------------------------------


def encode_preview_for_mcp(
    image_source: Union[str, bytes, BytesIO],
    *,
    max_dim: int = 512,
    max_b64_chars: int = 100_000,
    quality: int = 70,
    cache_key: Optional[str] = None,
) -> EncodedImage:
    """Encode an image for MCP responses with a base64 budget.

    Tries a deterministic quality/downscale ladder until the result fits.
    """
    if not _PIL:
        raise ImportError("Pillow is required for image processing")

    if cache_key:
        cached = _preview_cache.get(cache_key)
        if cached:
            return cached

    # Load image bytes
    if isinstance(image_source, str):
        if image_source.startswith(("http://", "https://")):
            raw = fetch_asset_bytes(image_source)
            src = BytesIO(raw)
        else:
            if not os.path.exists(image_source):
                raise FileNotFoundError(image_source)
            src = image_source
    elif isinstance(image_source, bytes):
        src = BytesIO(image_source)
    else:
        src = image_source

    with Image.open(src) as loaded:
        im = ImageOps.exif_transpose(loaded)
        if im.mode not in ("RGB", "RGBA", "LA", "L"):
            im = im.convert("RGB")

    quality_levels = [quality, 55, 40]
    dim_targets = [max_dim, 384, 256]
    prefix_len = len("data:image/webp;base64,")

    for dim in dim_targets:
        w, h = im.size
        if max(w, h) > dim:
            s = dim / max(w, h)
            resized = im.resize((max(1, int(w * s)), max(1, int(h * s))), Image.Resampling.LANCZOS)
        else:
            resized = im

        for q in quality_levels:
            buf = BytesIO()
            kw: dict[str, Any] = {"format": "WEBP", "quality": q, "method": 5}
            if resized.mode in ("RGBA", "LA"):
                kw["lossless"] = False
            resized.save(buf, **kw)
            raw = buf.getvalue()
            b64 = base64.b64encode(raw).decode("ascii")
            if len(b64) + prefix_len <= max_b64_chars:
                result = EncodedImage(
                    b64=b64,
                    mime_type="image/webp",
                    size_px=resized.size,
                    bytes_len=len(raw),
                    b64_chars=len(b64),
                    raw_bytes=raw,
                )
                if cache_key:
                    if len(_preview_cache) > 100:
                        _preview_cache.pop(next(iter(_preview_cache)))
                    _preview_cache[cache_key] = result
                return result

    # Last resort
    w, h = im.size
    if max(w, h) > 256:
        s = 256 / max(w, h)
        resized = im.resize((max(1, int(w * s)), max(1, int(h * s))), Image.Resampling.LANCZOS)
    else:
        resized = im
    buf = BytesIO()
    resized.save(buf, format="WEBP", quality=35, method=5)
    raw = buf.getvalue()
    b64 = base64.b64encode(raw).decode("ascii")
    if len(b64) + prefix_len > max_b64_chars:
        raise ValueError(f"Image exceeds base64 budget even at 256px q=35: {len(b64)} chars")

    result = EncodedImage(
        b64=b64, mime_type="image/webp", size_px=resized.size,
        bytes_len=len(raw), b64_chars=len(b64), raw_bytes=raw,
    )
    if cache_key:
        if len(_preview_cache) > 100:
            _preview_cache.pop(next(iter(_preview_cache)))
        _preview_cache[cache_key] = result
    return result

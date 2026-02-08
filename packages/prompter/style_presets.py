# style_presets.py - Style presets and prompt enhancement

STYLE_PRESETS = {
    "None": {
        "positive": "",
        "negative": "",
        "description": "No style modification"
    },
    "Photorealistic": {
        "positive": "photorealistic, hyperrealistic, 8k uhd, high detail, professional photography, natural lighting",
        "negative": "cartoon, anime, illustration, painting, drawing, art, cgi, 3d render, low quality",
        "description": "Realistic photo-like images"
    },
    "Anime": {
        "positive": "anime style, anime art, detailed anime, vibrant colors, cel shading, studio ghibli quality",
        "negative": "photorealistic, photo, 3d render, realistic, western cartoon, low quality",
        "description": "Japanese anime style"
    },
    "3D Render": {
        "positive": "3d render, octane render, cinema 4d, blender render, high detail, ray tracing, volumetric lighting",
        "negative": "2d, flat, painting, photograph, low poly, pixelated",
        "description": "High-quality 3D rendered look"
    },
    "Digital Art": {
        "positive": "digital art, digital painting, artstation, concept art, detailed, vibrant colors",
        "negative": "photo, photograph, realistic, low quality, blurry",
        "description": "Digital artwork style"
    },
    "Oil Painting": {
        "positive": "oil painting, classical art, renaissance style, brush strokes, canvas texture, masterpiece",
        "negative": "photo, digital, modern, low quality, amateur",
        "description": "Classical oil painting look"
    },
    "Watercolor": {
        "positive": "watercolor painting, soft colors, flowing, artistic, delicate, paper texture",
        "negative": "digital, sharp, photo, 3d render, harsh lines",
        "description": "Soft watercolor style"
    },
    "Cyberpunk": {
        "positive": "cyberpunk, neon lights, futuristic, dystopian, high tech, rain, night city, blade runner style",
        "negative": "nature, pastoral, vintage, old, medieval, low tech",
        "description": "Futuristic cyberpunk aesthetic"
    },
    "Fantasy": {
        "positive": "fantasy art, magical, ethereal, epic, detailed, mystical atmosphere, enchanted",
        "negative": "modern, realistic, mundane, boring, low quality",
        "description": "Epic fantasy style"
    },
    "Minimalist": {
        "positive": "minimalist, simple, clean, elegant, white space, modern design",
        "negative": "cluttered, busy, complex, detailed, ornate",
        "description": "Clean minimalist design"
    },
    "Vintage": {
        "positive": "vintage, retro, nostalgic, film grain, warm tones, 1970s aesthetic",
        "negative": "modern, digital, clean, sharp, futuristic",
        "description": "Retro vintage look"
    },
    "Comic Book": {
        "positive": "comic book style, bold lines, halftone dots, dynamic, superhero art, vibrant",
        "negative": "realistic, photo, subtle, muted colors",
        "description": "Bold comic book style"
    },
    "Pixel Art": {
        "positive": "pixel art, 16-bit, retro game style, pixelated, sprite art",
        "negative": "high resolution, smooth, realistic, 3d",
        "description": "Retro pixel art style"
    },
    "Funko Pop": {
        "positive": "funko pop style, vinyl figure, chibi, cute, big head, small body, collectible figure",
        "negative": "realistic proportions, detailed face, photorealistic",
        "description": "Cute Funko Pop figure style"
    },
    "Isometric": {
        "positive": "isometric view, isometric art, game asset, clean lines, 3d isometric, diorama",
        "negative": "perspective, realistic, fisheye, wide angle",
        "description": "Isometric game-style view"
    }
}

QUALITY_TAGS = {
    "High Quality": "masterpiece, best quality, high resolution, detailed, sharp focus",
    "Ultra Detailed": "ultra detailed, intricate details, highly detailed, 8k uhd",
    "Professional": "professional, award winning, trending on artstation",
    "Cinematic": "cinematic lighting, dramatic, movie still, film grain",
    "Studio": "studio lighting, professional photography, softbox lighting"
}

NEGATIVE_PRESETS = {
    "General": "low quality, worst quality, blurry, pixelated, ugly, deformed, disfigured",
    "Faces": "bad anatomy, bad hands, missing fingers, extra fingers, mutated hands, bad proportions",
    "NSFW Filter": "nsfw, nude, naked, sexual, explicit, gore, violence, disturbing",
    "Watermarks": "watermark, signature, text, logo, banner, username"
}


def build_enhanced_prompt(base_prompt: str, style: str = "None",
                          quality_tags: list = None,
                          custom_positive: str = "") -> str:
    """
    Build an enhanced prompt with style and quality tags

    Args:
        base_prompt: The user's original prompt
        style: Style preset name
        quality_tags: List of quality tag names to include
        custom_positive: Additional custom positive prompt

    Returns:
        Enhanced prompt string
    """
    parts = [base_prompt]

    # Add style positive
    if style and style in STYLE_PRESETS:
        style_positive = STYLE_PRESETS[style]["positive"]
        if style_positive:
            parts.append(style_positive)

    # Add quality tags
    if quality_tags:
        for tag in quality_tags:
            if tag in QUALITY_TAGS:
                parts.append(QUALITY_TAGS[tag])

    # Add custom positive
    if custom_positive:
        parts.append(custom_positive)

    return ", ".join(filter(None, parts))


def build_negative_prompt(style: str = "None",
                          negative_presets: list = None,
                          custom_negative: str = "") -> str:
    """
    Build a negative prompt from style and presets

    Args:
        style: Style preset name (for style-specific negatives)
        negative_presets: List of negative preset names
        custom_negative: Additional custom negative prompt

    Returns:
        Negative prompt string
    """
    parts = []

    # Add style negative
    if style and style in STYLE_PRESETS:
        style_negative = STYLE_PRESETS[style]["negative"]
        if style_negative:
            parts.append(style_negative)

    # Add negative presets
    if negative_presets:
        for preset in negative_presets:
            if preset in NEGATIVE_PRESETS:
                parts.append(NEGATIVE_PRESETS[preset])

    # Add custom negative
    if custom_negative:
        parts.append(custom_negative)

    return ", ".join(filter(None, parts))

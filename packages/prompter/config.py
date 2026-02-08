# config.py - Configuration for ComfyUI Prompter

import os
from pathlib import Path

# ComfyUI Configuration
COMFYUI_URL = "http://127.0.0.1:8188"  # Default ComfyUI address
COMFYUI_PATH = Path("D:/Projects/ComfyUI")  # ComfyUI installation directory

# API Server Configuration
API_SERVER_HOST = "127.0.0.1"
API_SERVER_PORT = 5050

# Output paths
OUTPUT_3D_PATH = Path("D:/Projects/ComfyUI/output/3D")

# Default workflows for pipelines
DEFAULT_TEXT_TO_IMAGE_WORKFLOW = "Default_Comfy_Workflow.json"
DEFAULT_3D_WORKFLOW = "triposg_image_to_3d.json"

# Ollama Configuration
OLLAMA_MODEL = "llama3.2"
OLLAMA_URL = "http://localhost:11434"

# Paths - UPDATED WITH YOUR PATHS (using forward slashes)
COMFYUI_WORKFLOWS_PATH = Path("D:/workflows")
COMFYUI_CHECKPOINTS_PATH = Path("D:/Projects/ComfyUI/models/checkpoints")
COMFYUI_DIFFUSION_MODELS_PATH = Path("D:/Projects/ComfyUI/models/diffusion_models")

# Model folders mapping for model_downloader.py
MODEL_FOLDERS = {
    "checkpoints": Path("D:/Projects/ComfyUI/models/checkpoints"),
    "diffusion_models": Path("D:/Projects/ComfyUI/models/diffusion_models"),
    "vae": Path("D:/Projects/ComfyUI/models/vae"),
    "clip": Path("D:/Projects/ComfyUI/models/clip"),
    "text_encoders": Path("D:/Projects/ComfyUI/models/text_encoders"),
    "controlnet": Path("D:/Projects/ComfyUI/models/controlnet"),
    "upscale_models": Path("D:/Projects/ComfyUI/models/upscale_models"),
    "loras": Path("D:/Projects/ComfyUI/models/loras"),
    "diffusers": Path("D:/Projects/ComfyUI/models/diffusers"),
    "tts": Path("D:/Projects/ComfyUI/models/tts"),
}

# Workflow Database
# Format: "workflow_filename": {"description": "", "checkpoint": "", "type": "", "use_case": ""}
WORKFLOWS = {
    # ==========================================================================
    # TEXT TO IMAGE WORKFLOWS
    # ==========================================================================
    "Default_Comfy_Workflow.json": {
        "description": "Basic Text to Image - Standard ComfyUI workflow",
        "checkpoint": "any",
        "type": "text_to_image",
        "use_case": "generating images from text prompts, general purpose image generation"
    },
    "NSFW Flux 1 Dev GGUF TXT2IMG with UltraRealistic Lora.json": {
        "description": "FLUX Text to Image - High quality with LoRA",
        "checkpoint": "flux1-dev-Q6_K.gguf",
        "type": "text_to_image",
        "use_case": "high quality realistic images from text prompts"
    },

    # ==========================================================================
    # IMAGE MANIPULATION WORKFLOWS
    # ==========================================================================
    "EP19 SDXL INPAINT.json": {
        "description": "Inpainting - Fill in masked areas of images",
        "checkpoint": "Juggernaut_X_RunDiffusion",
        "type": "2d_image",
        "use_case": "fixing images, removing objects, filling in missing parts"
    },
    "EP20 Flux Dev Q8 Sketch 2 Image.json": {
        "description": "Sketch to Image - Convert sketches to realistic images",
        "checkpoint": "flux1-dev-fp8.safetensors",
        "type": "2d_image",
        "use_case": "converting sketches, drawings, or wireframes into photorealistic images"
    },
    "EP20 Flux Dev Q8 Sketch 2 Image and Poses.json": {
        "description": "Sketch to Image with Poses - Convert sketches with pose control",
        "checkpoint": "flux1-dev-fp8.safetensors",
        "type": "2d_image",
        "use_case": "converting sketches with specific poses or body positions"
    },

    # ==========================================================================
    # CONVERSION WORKFLOWS
    # ==========================================================================
    "Image To Vector SVG.json": {
        "description": "Image to SVG - Convert raster images to vector SVG",
        "checkpoint": None,
        "type": "conversion",
        "use_case": "converting photos or images to scalable vector graphics"
    },
    "Flux Vector SVG Workflow Update.json": {
        "description": "FLUX Vector SVG - Generate vector graphics with FLUX",
        "checkpoint": "flux1-dev-fp8.safetensors",
        "type": "conversion",
        "use_case": "generating vector graphics and SVG files"
    },

    # ==========================================================================
    # 3D GENERATION WORKFLOWS
    # ==========================================================================
    "triposg_image_to_3d.json": {
        "description": "TripoSG Image to 3D - Fast 3D generation by Stability AI + Tripo",
        "checkpoint": "VAST-AI/TripoSG",
        "type": "3d_generation",
        "use_case": "fast 3D drafts, quick prototyping (<2 min on RTX 3070)"
    },
    "triposg_simple.json": {
        "description": "TripoSG Simple - Simplified fast 3D generation",
        "checkpoint": "VAST-AI/TripoSG",
        "type": "3d_generation",
        "use_case": "simple 3D generation with minimal settings"
    },
    "TripoSG.json": {
        "description": "TripoSG Full - Complete TripoSG workflow",
        "checkpoint": "VAST-AI/TripoSG",
        "type": "3d_generation",
        "use_case": "full-featured TripoSG 3D generation"
    },
    "hy3d_example_01 (1) - Copy.json": {
        "description": "Hunyuan3D v2.0 Full Pipeline - Image to textured 3D with delighting",
        "checkpoint": "hunyuan3d-dit-v2-0-fp16.safetensors",
        "type": "3d_generation",
        "use_case": "high-quality 3D models with textures from single images"
    },
    "Tripo-单图生3D.json": {
        "description": "Tripo Single Image to 3D - Chinese Tripo workflow",
        "checkpoint": "VAST-AI/TripoSG",
        "type": "3d_generation",
        "use_case": "single image to 3D model conversion"
    },
    "Tripo-多视图生3D.json": {
        "description": "Tripo Multi-View to 3D - Generate 3D from multiple views",
        "checkpoint": "VAST-AI/TripoSG",
        "type": "3d_generation",
        "use_case": "3D generation from multiple view images for better accuracy"
    },

    # ==========================================================================
    # VIDEO GENERATION WORKFLOWS
    # ==========================================================================
    "text_to_video_wan.json": {
        "description": "Text to Video - Generate videos from text descriptions using Wan 2.1",
        "checkpoint": "wan2.1_t2v_1.3B_fp16.safetensors",
        "type": "video_generation",
        "use_case": "creating videos from text prompts, animation generation"
    },
    "Wan+2.1+Image+to+Video+14B+480p+Q4_K_S+GGUF.json": {
        "description": "Image to Video - Animate images using Wan 2.1 VACE 14B (GGUF quantized)",
        "checkpoint": "Wan2.1_14B_VACE-Q4_K_M.gguf",
        "type": "video_generation",
        "use_case": "animating still images, image-to-video conversion, creating motion from photos"
    },
    "混元1.5+文生视频720P.json": {
        "description": "Hunyuan 1.5 Text to Video 720P - High resolution video generation",
        "checkpoint": "hunyuan_video_720_cfgdistill_fp8_e4m3fn.safetensors",
        "type": "video_generation",
        "use_case": "high resolution 720p video generation from text"
    },
    "混元图生视频+HunyuanVideoImagesGuider.json": {
        "description": "Hunyuan Image to Video - Animate images with Hunyuan",
        "checkpoint": "hunyuan_video_720_cfgdistill_fp8_e4m3fn.safetensors",
        "type": "video_generation",
        "use_case": "image animation and video generation with Hunyuan model"
    },

    # ==========================================================================
    # STYLE WORKFLOWS
    # ==========================================================================
    "RETROFUTURE STYLES Workflow Updated.json": {
        "description": "Retrofuture Styles - Generate retro-futuristic images",
        "checkpoint": "flux1-dev-fp8.safetensors",
        "type": "2d_image",
        "use_case": "creating retro-futuristic styled images"
    },
    "RETROFUTURE ASTRONAUT STYLES Workflow Updated.json": {
        "description": "Retrofuture Astronaut - Retro sci-fi astronaut imagery",
        "checkpoint": "flux1-dev-fp8.safetensors",
        "type": "2d_image",
        "use_case": "retro-futuristic astronaut and space imagery"
    },
    "RETROFUTURE Space Landscape STYLES Workflow Updated.json": {
        "description": "Retrofuture Space Landscapes - Retro sci-fi environments",
        "checkpoint": "flux1-dev-fp8.safetensors",
        "type": "2d_image",
        "use_case": "retro-futuristic space and landscape imagery"
    },
}

# Available Checkpoints - UPDATE WITH YOUR ACTUAL MODELS
CHECKPOINTS = {
    # FLUX Models
    "flux1-dev-fp8.safetensors": {
        "type": "flux",
        "description": "FLUX Dev FP8 - High quality image generation",
        "best_for": "realistic images, sketch-to-image"
    },
    "flux1-dev-Q6_K.gguf": {
        "type": "flux_gguf",
        "description": "FLUX Dev GGUF Q6 - Quantized for lower VRAM",
        "best_for": "text-to-image on limited VRAM"
    },

    # SDXL Models
    "Juggernaut_X_RunDiffusion": {
        "type": "sdxl",
        "description": "SDXL-based model for photorealistic generation",
        "best_for": "inpainting, realistic photos"
    },
    "sdXL_v10VAEFix": {
        "type": "sdxl",
        "description": "Stable Diffusion XL with VAE fix",
        "best_for": "general image generation"
    },

    # 3D Models
    "hunyuan3d-dit-v2-0-fp16.safetensors": {
        "type": "3d",
        "description": "Hunyuan3D v2.0 - Original 3D generation model",
        "best_for": "image to 3D model conversion"
    },
    "hunyuan3d-dit-v2-5-fp16.safetensors": {
        "type": "3d",
        "description": "Hunyuan3D v2.5 - Improved geometry (1024 res) and PBR textures",
        "best_for": "high-quality 3D with better geometry and textures"
    },
    "hunyuan3d-dit-v2-turbo-fp16.safetensors": {
        "type": "3d",
        "description": "Hunyuan3D Turbo - Faster generation with minimal quality loss",
        "best_for": "quick 3D prototyping, faster iteration"
    },
    "hunyuan3d-dit-v2-mini-fp16.safetensors": {
        "type": "3d",
        "description": "Hunyuan3D Mini 0.6B - Lightweight, lower VRAM requirement (~6GB)",
        "best_for": "3D generation on lower-end GPUs"
    },
    "VAST-AI/TripoSG": {
        "type": "3d",
        "description": "TripoSG by Tripo AI + Stability AI - Fast image-to-3D",
        "best_for": "fast 3D drafts, quick previews (<2 min generation)"
    },

    # Video Models
    "wan2.1_t2v_1.3B_fp16.safetensors": {
        "type": "video",
        "description": "Wan 2.1 text-to-video 1.3B model",
        "best_for": "text to video generation"
    },
    "Wan2.1_14B_VACE-Q4_K_M.gguf": {
        "type": "video_gguf",
        "description": "Wan 2.1 VACE 14B quantized for image-to-video",
        "best_for": "image animation, image-to-video"
    },
    "hunyuan_video_720_cfgdistill_fp8_e4m3fn.safetensors": {
        "type": "video",
        "description": "Hunyuan Video 720P - High resolution video model",
        "best_for": "720p video generation"
    },
}

# Diffusion Models
DIFFUSION_MODELS = {
    # Hunyuan3D Models
    "hunyuan3d-dit-v2-0-fp16.safetensors": {
        "type": "3d_diffusion",
        "description": "Hunyuan3D v2.0 diffusion model",
        "best_for": "3D generation - balanced quality/speed"
    },
    "hunyuan3d-dit-v2-5-fp16.safetensors": {
        "type": "3d_diffusion",
        "description": "Hunyuan3D v2.5 - improved geometry and PBR",
        "best_for": "highest quality 3D generation"
    },
    "hunyuan3d-dit-v2-turbo-fp16.safetensors": {
        "type": "3d_diffusion",
        "description": "Hunyuan3D Turbo - fast generation",
        "best_for": "quick 3D iteration"
    },
    "hunyuan3d-dit-v2-mini-fp16.safetensors": {
        "type": "3d_diffusion",
        "description": "Hunyuan3D Mini - low VRAM",
        "best_for": "3D on limited hardware"
    },
    # TripoSG
    "VAST-AI/TripoSG": {
        "type": "3d_diffusion",
        "description": "TripoSG by Stability AI + Tripo",
        "best_for": "fast 3D drafts"
    },
    # Other
    "omnigen2_fp16": {
        "type": "general_diffusion",
        "description": "OmniGen general purpose diffusion",
        "best_for": "general image generation"
    }
}


# Helper functions for workflow management
def get_workflows_by_type(workflow_type: str) -> dict:
    """Get workflows filtered by type"""
    return {
        name: info for name, info in WORKFLOWS.items()
        if info.get('type') == workflow_type
    }


def get_3d_workflows() -> dict:
    """Get all 3D generation workflows"""
    return get_workflows_by_type('3d_generation')


def get_video_workflows() -> dict:
    """Get all video generation workflows"""
    return get_workflows_by_type('video_generation')


def get_text_to_image_workflows() -> dict:
    """Get all text-to-image workflows"""
    return get_workflows_by_type('text_to_image')

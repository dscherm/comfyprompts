# model_registry.py - Database of known models with download sources

from typing import Dict, Any, Optional, List

# Registry of commonly used models with their download sources
MODEL_REGISTRY: Dict[str, Dict[str, Any]] = {
    # ==========================================================================
    # FLUX Models
    # ==========================================================================
    "flux1-dev-fp8.safetensors": {
        "type": "checkpoints",
        "source": "huggingface",
        "repo_id": "black-forest-labs/FLUX.1-dev",
        "filename": "flux1-dev-fp8.safetensors",
        "description": "FLUX.1 Dev model (FP8 quantized) for high-quality image generation",
        "size_gb": 11.9,
        "requires_auth": True,
    },
    "flux1-dev.safetensors": {
        "type": "checkpoints",
        "source": "huggingface",
        "repo_id": "black-forest-labs/FLUX.1-dev",
        "filename": "flux1-dev.safetensors",
        "description": "FLUX.1 Dev model (full precision)",
        "size_gb": 23.8,
        "requires_auth": True,
    },
    "flux1-schnell.safetensors": {
        "type": "checkpoints",
        "source": "huggingface",
        "repo_id": "black-forest-labs/FLUX.1-schnell",
        "filename": "flux1-schnell.safetensors",
        "description": "FLUX.1 Schnell - fast inference model",
        "size_gb": 23.8,
        "requires_auth": False,
    },

    # FLUX GGUF Quantized Models
    "flux1-dev-Q6_K.gguf": {
        "type": "diffusion_models",
        "subfolder": "FLUX",
        "source": "huggingface",
        "repo_id": "city96/FLUX.1-dev-gguf",
        "filename": "flux1-dev-Q6_K.gguf",
        "description": "FLUX.1 Dev GGUF Q6_K quantized - lower VRAM usage",
        "size_gb": 9.1,
        "requires_auth": False,
    },
    "flux1-dev-Q8_0.gguf": {
        "type": "diffusion_models",
        "subfolder": "FLUX",
        "source": "huggingface",
        "repo_id": "city96/FLUX.1-dev-gguf",
        "filename": "flux1-dev-Q8_0.gguf",
        "description": "FLUX.1 Dev GGUF Q8 quantized - balanced quality/VRAM",
        "size_gb": 12.2,
        "requires_auth": False,
    },
    "flux1-dev-Q4_K_S.gguf": {
        "type": "diffusion_models",
        "subfolder": "FLUX",
        "source": "huggingface",
        "repo_id": "city96/FLUX.1-dev-gguf",
        "filename": "flux1-dev-Q4_K_S.gguf",
        "description": "FLUX.1 Dev GGUF Q4 quantized - lowest VRAM",
        "size_gb": 6.8,
        "requires_auth": False,
    },

    # ==========================================================================
    # SDXL Models
    # ==========================================================================
    "sd_xl_base_1.0.safetensors": {
        "type": "checkpoints",
        "source": "huggingface",
        "repo_id": "stabilityai/stable-diffusion-xl-base-1.0",
        "filename": "sd_xl_base_1.0.safetensors",
        "description": "Stable Diffusion XL Base 1.0",
        "size_gb": 6.9,
        "requires_auth": False,
    },
    "sd_xl_refiner_1.0.safetensors": {
        "type": "checkpoints",
        "source": "huggingface",
        "repo_id": "stabilityai/stable-diffusion-xl-refiner-1.0",
        "filename": "sd_xl_refiner_1.0.safetensors",
        "description": "Stable Diffusion XL Refiner 1.0",
        "size_gb": 6.1,
        "requires_auth": False,
    },
    "sd_xl_base_1.0_inpainting_0.1.safetensors": {
        "type": "checkpoints",
        "source": "huggingface",
        "repo_id": "diffusers/stable-diffusion-xl-1.0-inpainting-0.1",
        "filename": "sd_xl_base_1.0_inpainting_0.1.safetensors",
        "description": "SDXL Inpainting model",
        "size_gb": 6.9,
        "requires_auth": False,
    },

    # Popular SDXL Fine-tunes
    "Juggernaut_X_RunDiffusion.safetensors": {
        "type": "checkpoints",
        "source": "civitai",
        "model_id": 133005,
        "version_id": 782002,
        "filename": "Juggernaut_X_RunDiffusion.safetensors",
        "description": "Juggernaut X - photorealistic SDXL fine-tune",
        "size_gb": 6.5,
        "requires_auth": False,
    },
    "dreamshaperXL_v21TurboDPMSDE.safetensors": {
        "type": "checkpoints",
        "source": "civitai",
        "model_id": 112902,
        "version_id": 351306,
        "filename": "dreamshaperXL_v21TurboDPMSDE.safetensors",
        "description": "DreamShaper XL Turbo - fast artistic generation",
        "size_gb": 6.5,
        "requires_auth": False,
    },
    "realvisxlV50_v50Bakedvae.safetensors": {
        "type": "checkpoints",
        "source": "civitai",
        "model_id": 139562,
        "version_id": 789646,
        "filename": "realvisxlV50_v50Bakedvae.safetensors",
        "description": "RealVisXL V5.0 - photorealistic with baked VAE",
        "size_gb": 6.5,
        "requires_auth": False,
    },

    # ==========================================================================
    # SD 1.5 Models
    # ==========================================================================
    "v1-5-pruned-emaonly.safetensors": {
        "type": "checkpoints",
        "source": "huggingface",
        "repo_id": "stable-diffusion-v1-5/stable-diffusion-v1-5",
        "filename": "v1-5-pruned-emaonly.safetensors",
        "description": "Stable Diffusion 1.5 (EMA only, pruned)",
        "size_gb": 4.3,
        "requires_auth": False,
    },

    # ==========================================================================
    # 3D Generation Models - Hunyuan3D
    # ==========================================================================
    "hunyuan3d-dit-v2-0-fp16.safetensors": {
        "type": "diffusion_models",
        "subfolder": "hy3dgen",
        "source": "huggingface",
        "repo_id": "Kijai/Hunyuan3D-2_safetensors",
        "filename": "hunyuan3d-dit-v2-0-fp16.safetensors",
        "description": "Hunyuan3D DiT v2.0 for image-to-3D generation",
        "size_gb": 4.5,
        "requires_auth": False,
    },
    "hunyuan3d-dit-v2-5-fp16.safetensors": {
        "type": "diffusion_models",
        "subfolder": "hy3dgen",
        "source": "huggingface",
        "repo_id": "tencent/Hunyuan3D-2",
        "filename": "hunyuan3d-dit-v2-5-fp16.safetensors",
        "description": "Hunyuan3D DiT v2.5 - improved geometry (1024 res), better PBR textures",
        "size_gb": 4.8,
        "requires_auth": False,
    },
    "hunyuan3d-dit-v2-turbo-fp16.safetensors": {
        "type": "diffusion_models",
        "subfolder": "hy3dgen",
        "source": "huggingface",
        "repo_id": "tencent/Hunyuan3D-2",
        "filename": "hunyuan3d-dit-v2-turbo-fp16.safetensors",
        "description": "Hunyuan3D Turbo - faster 3D generation with minimal quality loss",
        "size_gb": 4.5,
        "requires_auth": False,
    },
    "hunyuan3d-dit-v2-mini-fp16.safetensors": {
        "type": "diffusion_models",
        "subfolder": "hy3dgen",
        "source": "huggingface",
        "repo_id": "tencent/Hunyuan3D-2",
        "filename": "hunyuan3d-dit-v2-mini-fp16.safetensors",
        "description": "Hunyuan3D Mini 0.6B - lightweight, lower VRAM (~6GB)",
        "size_gb": 1.2,
        "requires_auth": False,
    },
    "hunyuan3d-paint-v2-0": {
        "type": "diffusers",
        "source": "huggingface",
        "repo_id": "tencent/Hunyuan3D-2",
        "filename": "hunyuan3d-paint-v2-0",
        "description": "Hunyuan3D Paint model for multiview texture generation",
        "size_gb": 2.5,
        "requires_auth": False,
        "is_folder": True,
    },
    "hunyuan3d-delight-v2-0": {
        "type": "diffusers",
        "source": "huggingface",
        "repo_id": "tencent/Hunyuan3D-2",
        "filename": "hunyuan3d-delight-v2-0",
        "description": "Hunyuan3D Delight model for removing lighting from reference images",
        "size_gb": 2.0,
        "requires_auth": False,
        "is_folder": True,
    },

    # ==========================================================================
    # 3D Generation Models - TripoSG
    # ==========================================================================
    "VAST-AI/TripoSG": {
        "type": "diffusers",
        "source": "huggingface",
        "repo_id": "VAST-AI/TripoSG",
        "filename": "TripoSG",
        "description": "TripoSG by Tripo AI + Stability AI - fast image-to-3D (<2min on RTX 3070)",
        "size_gb": 7.95,
        "requires_auth": False,
        "is_folder": True,
        "install_path": "ComfyUI/models/diffusers/TripoSG",
    },

    # ==========================================================================
    # Video Generation Models - Wan 2.1
    # ==========================================================================
    "wan2.1_t2v_1.3B_fp16.safetensors": {
        "type": "diffusion_models",
        "source": "huggingface",
        "repo_id": "Comfy-Org/Wan_2.1_ComfyUI_repackaged",
        "filename": "split_files/diffusion_models/wan2.1_t2v_1.3B_fp16.safetensors",
        "description": "Wan 2.1 Text-to-Video 1.3B model",
        "size_gb": 2.6,
        "requires_auth": False,
    },
    "wan2.1_i2v_720p_14B_fp16.safetensors": {
        "type": "diffusion_models",
        "source": "huggingface",
        "repo_id": "Wan-AI/Wan2.1-I2V-14B-720P",
        "filename": "wan2.1_i2v_720p_14B_fp16.safetensors",
        "description": "Wan 2.1 Image-to-Video 14B 720p model (full precision)",
        "size_gb": 28.0,
        "requires_auth": False,
    },
    "Wan2.1_14B_VACE-Q4_K_M.gguf": {
        "type": "diffusion_models",
        "source": "huggingface",
        "repo_id": "QuantStack/Wan2.1_14B_VACE-GGUF",
        "filename": "Wan2.1_14B_VACE-Q4_K_M.gguf",
        "description": "Wan 2.1 VACE 14B (GGUF Q4 quantized) for image-to-video",
        "size_gb": 8.5,
        "requires_auth": False,
    },
    "Wan2.1_14B_VACE-Q8_0.gguf": {
        "type": "diffusion_models",
        "source": "huggingface",
        "repo_id": "QuantStack/Wan2.1_14B_VACE-GGUF",
        "filename": "Wan2.1_14B_VACE-Q8_0.gguf",
        "description": "Wan 2.1 VACE 14B (GGUF Q8 quantized) - higher quality",
        "size_gb": 15.2,
        "requires_auth": False,
    },
    "umt5_xxl_fp8_e4m3fn_scaled.safetensors": {
        "type": "text_encoders",
        "source": "huggingface",
        "repo_id": "Comfy-Org/Wan_2.1_ComfyUI_repackaged",
        "filename": "split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors",
        "description": "UMT5-XXL text encoder for Wan 2.1 (FP8 quantized)",
        "size_gb": 4.9,
        "requires_auth": False,
    },
    "wan_2.1_vae.safetensors": {
        "type": "vae",
        "source": "huggingface",
        "repo_id": "Comfy-Org/Wan_2.1_ComfyUI_repackaged",
        "filename": "split_files/vae/wan_2.1_vae.safetensors",
        "description": "Wan 2.1 VAE for video generation",
        "size_gb": 0.2,
        "requires_auth": False,
    },

    # ==========================================================================
    # Video Generation Models - Hunyuan Video
    # ==========================================================================
    "hunyuan_video_720_cfgdistill_fp8_e4m3fn.safetensors": {
        "type": "diffusion_models",
        "source": "huggingface",
        "repo_id": "Comfy-Org/HunyuanVideo_repackaged",
        "filename": "split_files/diffusion_models/hunyuan_video_720_cfgdistill_fp8_e4m3fn.safetensors",
        "description": "Hunyuan Video 720P CFG Distilled (FP8)",
        "size_gb": 12.5,
        "requires_auth": False,
    },
    "hunyuan_video_vae_bf16.safetensors": {
        "type": "vae",
        "source": "huggingface",
        "repo_id": "Comfy-Org/HunyuanVideo_repackaged",
        "filename": "split_files/vae/hunyuan_video_vae_bf16.safetensors",
        "description": "Hunyuan Video VAE (BF16)",
        "size_gb": 0.8,
        "requires_auth": False,
    },
    "llava_llama3_fp8_scaled.safetensors": {
        "type": "text_encoders",
        "source": "huggingface",
        "repo_id": "Comfy-Org/HunyuanVideo_repackaged",
        "filename": "split_files/text_encoders/llava_llama3_fp8_scaled.safetensors",
        "description": "LLaVA-LLaMA3 text encoder for Hunyuan Video (FP8)",
        "size_gb": 4.5,
        "requires_auth": False,
    },
    "clip_l_hunyuan_video.safetensors": {
        "type": "text_encoders",
        "source": "huggingface",
        "repo_id": "Comfy-Org/HunyuanVideo_repackaged",
        "filename": "split_files/text_encoders/clip_l.safetensors",
        "description": "CLIP-L text encoder for Hunyuan Video",
        "size_gb": 0.2,
        "requires_auth": False,
    },

    # ==========================================================================
    # VAE Models
    # ==========================================================================
    "sdxl_vae.safetensors": {
        "type": "vae",
        "source": "huggingface",
        "repo_id": "stabilityai/sdxl-vae",
        "filename": "sdxl_vae.safetensors",
        "description": "SDXL VAE (separate)",
        "size_gb": 0.3,
        "requires_auth": False,
    },
    "ae.safetensors": {
        "type": "vae",
        "source": "huggingface",
        "repo_id": "black-forest-labs/FLUX.1-dev",
        "filename": "ae.safetensors",
        "description": "FLUX VAE/Autoencoder",
        "size_gb": 0.3,
        "requires_auth": True,
    },
    "vae-ft-mse-840000-ema-pruned.safetensors": {
        "type": "vae",
        "source": "huggingface",
        "repo_id": "stabilityai/sd-vae-ft-mse-original",
        "filename": "vae-ft-mse-840000-ema-pruned.safetensors",
        "description": "SD VAE fine-tuned MSE (for SD 1.5)",
        "size_gb": 0.3,
        "requires_auth": False,
    },

    # ==========================================================================
    # CLIP / Text Encoder Models
    # ==========================================================================
    "clip_l.safetensors": {
        "type": "clip",
        "source": "huggingface",
        "repo_id": "comfyanonymous/flux_text_encoders",
        "filename": "clip_l.safetensors",
        "description": "CLIP-L text encoder for FLUX",
        "size_gb": 0.2,
        "requires_auth": False,
    },
    "t5xxl_fp16.safetensors": {
        "type": "clip",
        "source": "huggingface",
        "repo_id": "comfyanonymous/flux_text_encoders",
        "filename": "t5xxl_fp16.safetensors",
        "description": "T5-XXL text encoder for FLUX (FP16)",
        "size_gb": 9.8,
        "requires_auth": False,
    },
    "t5xxl_fp8_e4m3fn.safetensors": {
        "type": "clip",
        "source": "huggingface",
        "repo_id": "comfyanonymous/flux_text_encoders",
        "filename": "t5xxl_fp8_e4m3fn.safetensors",
        "description": "T5-XXL text encoder for FLUX (FP8 quantized)",
        "size_gb": 4.9,
        "requires_auth": False,
    },
    "t5-v1_1-xxl-encoder-Q5_K_M.gguf": {
        "type": "text_encoders",
        "source": "huggingface",
        "repo_id": "city96/t5-v1_1-xxl-encoder-gguf",
        "filename": "t5-v1_1-xxl-encoder-Q5_K_M.gguf",
        "description": "T5-XXL encoder GGUF Q5 for lower VRAM",
        "size_gb": 4.7,
        "requires_auth": False,
    },
    "t5-v1_1-xxl-encoder-Q8_0.gguf": {
        "type": "text_encoders",
        "source": "huggingface",
        "repo_id": "city96/t5-v1_1-xxl-encoder-gguf",
        "filename": "t5-v1_1-xxl-encoder-Q8_0.gguf",
        "description": "T5-XXL encoder GGUF Q8 for balanced quality",
        "size_gb": 7.2,
        "requires_auth": False,
    },

    # ==========================================================================
    # ControlNet Models
    # ==========================================================================
    "control-lora-canny-rank256.safetensors": {
        "type": "controlnet",
        "source": "huggingface",
        "repo_id": "stabilityai/control-lora",
        "filename": "control-lora-canny-rank256.safetensors",
        "description": "ControlNet LoRA for canny edge detection (SDXL)",
        "size_gb": 0.8,
        "requires_auth": False,
    },
    "control-lora-depth-rank256.safetensors": {
        "type": "controlnet",
        "source": "huggingface",
        "repo_id": "stabilityai/control-lora",
        "filename": "control-lora-depth-rank256.safetensors",
        "description": "ControlNet LoRA for depth maps (SDXL)",
        "size_gb": 0.8,
        "requires_auth": False,
    },
    "diffusers_xl_canny_full.safetensors": {
        "type": "controlnet",
        "source": "huggingface",
        "repo_id": "diffusers/controlnet-canny-sdxl-1.0",
        "filename": "diffusers_xl_canny_full.safetensors",
        "description": "Full ControlNet Canny for SDXL",
        "size_gb": 2.5,
        "requires_auth": False,
    },
    "diffusers_xl_depth_full.safetensors": {
        "type": "controlnet",
        "source": "huggingface",
        "repo_id": "diffusers/controlnet-depth-sdxl-1.0",
        "filename": "diffusers_xl_depth_full.safetensors",
        "description": "Full ControlNet Depth for SDXL",
        "size_gb": 2.5,
        "requires_auth": False,
    },

    # FLUX ControlNets
    "flux_controlnet_canny.safetensors": {
        "type": "controlnet",
        "source": "huggingface",
        "repo_id": "XLabs-AI/flux-controlnet-collections",
        "filename": "flux-canny-controlnet-v3.safetensors",
        "description": "FLUX ControlNet for canny edge detection",
        "size_gb": 3.6,
        "requires_auth": False,
    },
    "flux_controlnet_depth.safetensors": {
        "type": "controlnet",
        "source": "huggingface",
        "repo_id": "XLabs-AI/flux-controlnet-collections",
        "filename": "flux-depth-controlnet-v3.safetensors",
        "description": "FLUX ControlNet for depth maps",
        "size_gb": 3.6,
        "requires_auth": False,
    },

    # ==========================================================================
    # Upscaler Models
    # ==========================================================================
    "RealESRGAN_x4plus.pth": {
        "type": "upscale_models",
        "source": "huggingface",
        "repo_id": "ai-forever/Real-ESRGAN",
        "filename": "RealESRGAN_x4plus.pth",
        "description": "Real-ESRGAN 4x upscaler",
        "size_gb": 0.07,
        "requires_auth": False,
    },
    "RealESRGAN_x4plus_anime_6B.pth": {
        "type": "upscale_models",
        "source": "huggingface",
        "repo_id": "ai-forever/Real-ESRGAN",
        "filename": "RealESRGAN_x4plus_anime_6B.pth",
        "description": "Real-ESRGAN 4x upscaler optimized for anime",
        "size_gb": 0.02,
        "requires_auth": False,
    },
    "4x-UltraSharp.pth": {
        "type": "upscale_models",
        "source": "huggingface",
        "repo_id": "Kim2091/UltraSharp",
        "filename": "4x-UltraSharp.pth",
        "description": "UltraSharp 4x upscaler - sharp details",
        "size_gb": 0.07,
        "requires_auth": False,
    },
    "4x_NMKD-Siax_200k.pth": {
        "type": "upscale_models",
        "source": "huggingface",
        "repo_id": "Kim2091/NMKD-Siax",
        "filename": "4x_NMKD-Siax_200k.pth",
        "description": "NMKD-Siax 4x upscaler",
        "size_gb": 0.07,
        "requires_auth": False,
    },

    # ==========================================================================
    # LoRA Models (Popular Examples)
    # ==========================================================================
    "lcm-lora-sdxl.safetensors": {
        "type": "loras",
        "source": "huggingface",
        "repo_id": "latent-consistency/lcm-lora-sdxl",
        "filename": "pytorch_lora_weights.safetensors",
        "description": "LCM LoRA for SDXL - faster inference (4-8 steps)",
        "size_gb": 0.4,
        "requires_auth": False,
    },
    "lcm-lora-sdv1-5.safetensors": {
        "type": "loras",
        "source": "huggingface",
        "repo_id": "latent-consistency/lcm-lora-sdv1-5",
        "filename": "pytorch_lora_weights.safetensors",
        "description": "LCM LoRA for SD 1.5 - faster inference",
        "size_gb": 0.07,
        "requires_auth": False,
    },

    # ==========================================================================
    # TTS/Audio Models
    # ==========================================================================
    "xtts_v2": {
        "type": "tts",
        "source": "huggingface",
        "repo_id": "coqui/XTTS-v2",
        "filename": "model.pth",
        "description": "Coqui XTTS-v2 for high-quality TTS with voice cloning",
        "size_gb": 1.8,
        "requires_auth": False,
    },
    "kokoro-v0_19": {
        "type": "tts",
        "source": "huggingface",
        "repo_id": "hexgrad/Kokoro-82M",
        "filename": "kokoro-v0_19.pth",
        "description": "Kokoro-82M lightweight TTS model",
        "size_gb": 0.08,
        "requires_auth": False,
    },

    # ==========================================================================
    # IP-Adapter Models
    # ==========================================================================
    "ip-adapter_sdxl.safetensors": {
        "type": "ipadapter",
        "source": "huggingface",
        "repo_id": "h94/IP-Adapter",
        "filename": "sdxl_models/ip-adapter_sdxl.safetensors",
        "description": "IP-Adapter for SDXL - image prompt adapter",
        "size_gb": 0.7,
        "requires_auth": False,
    },
    "ip-adapter-plus_sdxl_vit-h.safetensors": {
        "type": "ipadapter",
        "source": "huggingface",
        "repo_id": "h94/IP-Adapter",
        "filename": "sdxl_models/ip-adapter-plus_sdxl_vit-h.safetensors",
        "description": "IP-Adapter Plus for SDXL with ViT-H encoder",
        "size_gb": 0.98,
        "requires_auth": False,
    },
    "ip-adapter-faceid_sdxl.bin": {
        "type": "ipadapter",
        "source": "huggingface",
        "repo_id": "h94/IP-Adapter-FaceID",
        "filename": "ip-adapter-faceid_sdxl.bin",
        "description": "IP-Adapter FaceID for SDXL - face preservation",
        "size_gb": 0.7,
        "requires_auth": False,
    },

    # ==========================================================================
    # CLIP Vision Models (for IP-Adapter)
    # ==========================================================================
    "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors": {
        "type": "clip_vision",
        "source": "huggingface",
        "repo_id": "h94/IP-Adapter",
        "filename": "models/image_encoder/model.safetensors",
        "description": "CLIP ViT-H vision encoder for IP-Adapter",
        "size_gb": 2.5,
        "requires_auth": False,
    },
    "CLIP-ViT-bigG-14-laion2B-39B-b160k.safetensors": {
        "type": "clip_vision",
        "source": "huggingface",
        "repo_id": "h94/IP-Adapter",
        "filename": "sdxl_models/image_encoder/model.safetensors",
        "description": "CLIP ViT-bigG vision encoder for IP-Adapter SDXL",
        "size_gb": 3.7,
        "requires_auth": False,
    },
}


def get_model_info(filename: str) -> Optional[Dict[str, Any]]:
    """Get model information from the registry by filename."""
    return MODEL_REGISTRY.get(filename)


def search_models(query: str) -> List[Dict[str, Any]]:
    """Search models by name or description."""
    query_lower = query.lower()
    results = []
    for filename, info in MODEL_REGISTRY.items():
        if (query_lower in filename.lower() or
            query_lower in info.get('description', '').lower()):
            results.append({'filename': filename, **info})
    return results


def get_models_by_type(model_type: str) -> List[Dict[str, Any]]:
    """Get all models of a specific type."""
    results = []
    for filename, info in MODEL_REGISTRY.items():
        if info.get('type') == model_type:
            results.append({'filename': filename, **info})
    return results


def get_models_by_source(source: str) -> List[Dict[str, Any]]:
    """Get all models from a specific source (huggingface, civitai)."""
    results = []
    for filename, info in MODEL_REGISTRY.items():
        if info.get('source', '').lower() == source.lower():
            results.append({'filename': filename, **info})
    return results


def get_3d_models() -> List[Dict[str, Any]]:
    """Get all 3D generation models."""
    results = []
    for filename, info in MODEL_REGISTRY.items():
        if '3d' in info.get('description', '').lower() or 'hunyuan3d' in filename.lower() or 'tripo' in filename.lower():
            results.append({'filename': filename, **info})
    return results


def get_video_models() -> List[Dict[str, Any]]:
    """Get all video generation models."""
    results = []
    for filename, info in MODEL_REGISTRY.items():
        desc = info.get('description', '').lower()
        if 'video' in desc or 'wan' in filename.lower() or 'hunyuan_video' in filename.lower():
            results.append({'filename': filename, **info})
    return results


def add_model_to_registry(filename: str, model_info: Dict[str, Any]) -> None:
    """Add a model to the registry (runtime only, not persisted)."""
    MODEL_REGISTRY[filename] = model_info


def get_required_models_for_workflow(workflow_data: dict) -> List[str]:
    """
    Analyze a workflow and return list of required model filenames.

    This function examines the workflow JSON to find all model references.
    """
    required = set()

    nodes = workflow_data.get('nodes', [])
    for node in nodes:
        widgets = node.get('widgets_values', [])
        node_type = node.get('type', '')

        # Check for checkpoint loaders
        if node_type in ['CheckpointLoaderSimple', 'CheckpointLoader',
                         'ImageOnlyCheckpointLoader', 'UNETLoader', 'UnetLoaderGGUF']:
            if widgets and isinstance(widgets[0], str):
                required.add(widgets[0])

        # Check for VAE loaders
        elif node_type == 'VAELoader':
            if widgets and isinstance(widgets[0], str):
                required.add(widgets[0])

        # Check for LoRA loaders
        elif node_type in ['LoraLoader', 'LoraLoaderModelOnly', 'Power Lora Loader (rgthree)']:
            for w in widgets:
                if isinstance(w, str) and w.endswith(('.safetensors', '.ckpt', '.pth', '.bin')):
                    required.add(w)

        # Check for ControlNet loaders
        elif node_type in ['ControlNetLoader', 'DiffControlNetLoader']:
            if widgets and isinstance(widgets[0], str):
                required.add(widgets[0])

        # Check for CLIP loaders
        elif node_type in ['CLIPLoader', 'DualCLIPLoader', 'DualCLIPLoaderGGUF']:
            for w in widgets:
                if isinstance(w, str) and w.endswith(('.safetensors', '.ckpt', '.pth', '.bin', '.gguf')):
                    required.add(w)

        # Check for upscaler loaders
        elif node_type in ['UpscaleModelLoader']:
            if widgets and isinstance(widgets[0], str):
                required.add(widgets[0])

        # Check for IP-Adapter loaders
        elif node_type in ['IPAdapterModelLoader', 'IPAdapterUnifiedLoader']:
            if widgets and isinstance(widgets[0], str):
                required.add(widgets[0])

    return list(required)


def get_downloadable_models(required_models: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Given a list of required model filenames, return info for models that are in the registry.

    Returns:
        Dict mapping filename to model info for models that can be auto-downloaded
    """
    downloadable = {}
    for model_name in required_models:
        info = get_model_info(model_name)
        if info:
            downloadable[model_name] = info
    return downloadable


def get_total_size_gb() -> float:
    """Get total size of all models in registry."""
    return sum(info.get('size_gb', 0) for info in MODEL_REGISTRY.values())


def get_registry_stats() -> Dict[str, Any]:
    """Get statistics about the model registry."""
    types = {}
    sources = {}
    total_size = 0

    for info in MODEL_REGISTRY.values():
        model_type = info.get('type', 'unknown')
        source = info.get('source', 'unknown')
        size = info.get('size_gb', 0)

        types[model_type] = types.get(model_type, 0) + 1
        sources[source] = sources.get(source, 0) + 1
        total_size += size

    return {
        'total_models': len(MODEL_REGISTRY),
        'total_size_gb': round(total_size, 2),
        'by_type': types,
        'by_source': sources,
    }

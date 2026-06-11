"""Built-in ComfyUI workflow templates for the Blender pipeline.

These are constructed in Python (not loaded from JSON files) so the addon
stays self-contained with no external file dependencies.  Each builder
returns a ComfyUI API-format workflow dict ready for queue_prompt().
"""

import random

# Default checkpoint — SDXL base, installed on this machine (SD 1.5 is not)
DEFAULT_CHECKPOINT = "sd_xl_base_1.0.safetensors"
DEFAULT_SAMPLER = "euler"
DEFAULT_SCHEDULER = "normal"


def build_img2img_workflow(
    image_name,
    prompt,
    negative_prompt="",
    checkpoint=DEFAULT_CHECKPOINT,
    steps=20,
    cfg=7.0,
    denoise=0.65,
    seed=None,
    sampler=DEFAULT_SAMPLER,
    scheduler=DEFAULT_SCHEDULER,
):
    """Build an img2img workflow that transforms an uploaded image.

    Args:
        image_name: Filename returned by ComfyUI's /upload/image endpoint.
        prompt: Positive text prompt.
        negative_prompt: Negative text prompt.
        checkpoint: Checkpoint model filename.
        steps: Number of sampling steps.
        cfg: Classifier-free guidance scale.
        denoise: Denoising strength (0.0 = no change, 1.0 = full regeneration).
        seed: Random seed (None = random).
        sampler: Sampler algorithm name.
        scheduler: Noise scheduler name.

    Returns:
        dict: ComfyUI API-format workflow.
    """
    if seed is None:
        seed = random.randint(0, 2**32 - 1)

    return {
        "1": {
            "inputs": {"ckpt_name": checkpoint},
            "class_type": "CheckpointLoaderSimple",
            "_meta": {"title": "Load Checkpoint"},
        },
        "2": {
            "inputs": {"image": image_name, "upload": "image"},
            "class_type": "LoadImage",
            "_meta": {"title": "Load Source Image"},
        },
        "3": {
            "inputs": {"pixels": ["2", 0], "vae": ["1", 2]},
            "class_type": "VAEEncode",
            "_meta": {"title": "Encode to Latent"},
        },
        "4": {
            "inputs": {"text": prompt, "clip": ["1", 1]},
            "class_type": "CLIPTextEncode",
            "_meta": {"title": "Positive Prompt"},
        },
        "5": {
            "inputs": {"text": negative_prompt or "", "clip": ["1", 1]},
            "class_type": "CLIPTextEncode",
            "_meta": {"title": "Negative Prompt"},
        },
        "6": {
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": sampler,
                "scheduler": scheduler,
                "denoise": denoise,
                "model": ["1", 0],
                "positive": ["4", 0],
                "negative": ["5", 0],
                "latent_image": ["3", 0],
            },
            "class_type": "KSampler",
            "_meta": {"title": "KSampler"},
        },
        "7": {
            "inputs": {"samples": ["6", 0], "vae": ["1", 2]},
            "class_type": "VAEDecode",
            "_meta": {"title": "VAE Decode"},
        },
        "8": {
            "inputs": {
                "filename_prefix": "blender_pipeline",
                "images": ["7", 0],
            },
            "class_type": "SaveImage",
            "_meta": {"title": "Save Image"},
        },
    }


def build_txt2img_workflow(
    prompt,
    negative_prompt="",
    checkpoint=DEFAULT_CHECKPOINT,
    width=512,
    height=512,
    steps=20,
    cfg=7.0,
    seed=None,
    sampler=DEFAULT_SAMPLER,
    scheduler=DEFAULT_SCHEDULER,
):
    """Build a txt2img workflow that generates an image from text.

    Args:
        prompt: Positive text prompt.
        negative_prompt: Negative text prompt.
        checkpoint: Checkpoint model filename.
        width: Output image width.
        height: Output image height.
        steps: Number of sampling steps.
        cfg: Classifier-free guidance scale.
        seed: Random seed (None = random).
        sampler: Sampler algorithm name.
        scheduler: Noise scheduler name.

    Returns:
        dict: ComfyUI API-format workflow.
    """
    if seed is None:
        seed = random.randint(0, 2**32 - 1)

    return {
        "1": {
            "inputs": {"ckpt_name": checkpoint},
            "class_type": "CheckpointLoaderSimple",
            "_meta": {"title": "Load Checkpoint"},
        },
        "2": {
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": 1,
            },
            "class_type": "EmptyLatentImage",
            "_meta": {"title": "Empty Latent"},
        },
        "3": {
            "inputs": {"text": prompt, "clip": ["1", 1]},
            "class_type": "CLIPTextEncode",
            "_meta": {"title": "Positive Prompt"},
        },
        "4": {
            "inputs": {"text": negative_prompt or "", "clip": ["1", 1]},
            "class_type": "CLIPTextEncode",
            "_meta": {"title": "Negative Prompt"},
        },
        "5": {
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": sampler,
                "scheduler": scheduler,
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["3", 0],
                "negative": ["4", 0],
                "latent_image": ["2", 0],
            },
            "class_type": "KSampler",
            "_meta": {"title": "KSampler"},
        },
        "6": {
            "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
            "class_type": "VAEDecode",
            "_meta": {"title": "VAE Decode"},
        },
        "7": {
            "inputs": {
                "filename_prefix": "blender_pipeline",
                "images": ["6", 0],
            },
            "class_type": "SaveImage",
            "_meta": {"title": "Save Image"},
        },
    }

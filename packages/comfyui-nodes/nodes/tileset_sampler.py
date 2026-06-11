"""Non-manifold diffusion tileset sampler for ComfyUI."""

import torch
import comfy.samplers
import comfy.sample
import comfy.model_management
import comfy.utils

from ..utils.marching_squares import MARCHING_SQUARES_CASES, get_3x3_neighbors
from ..utils.groupnorm_patch import patch_groupnorm


class NonManifoldTilesetSampler:
    """Generates 16 coherent marching squares tiles via non-manifold diffusion.

    At each denoising step, each tile is placed in a 3x3 context patch
    with valid neighbors. SharedGroupNorm forces consistent style across
    all tiles.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "positive": ("CONDITIONING",),
                "negative": ("CONDITIONING",),
                "vae": ("VAE",),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
                "steps": ("INT", {"default": 20, "min": 1, "max": 100}),
                "cfg": ("FLOAT", {"default": 7.0, "min": 0.0, "max": 30.0, "step": 0.1}),
                "sampler_name": (comfy.samplers.KSampler.SAMPLERS,),
                "scheduler": (comfy.samplers.KSampler.SCHEDULERS,),
                "tile_size": ("INT", {"default": 64, "min": 16, "max": 256}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "sample"
    CATEGORY = "tileset"

    def sample(self, model, positive, negative, vae, seed, steps, cfg,
               sampler_name, scheduler, tile_size):
        device = comfy.model_management.get_torch_device()
        generator = torch.Generator(device="cpu").manual_seed(seed)

        # 1. Create 16 random latent tensors [1, 4, tile_size, tile_size]
        latents = []
        for i in range(16):
            noise = torch.randn(1, 4, tile_size, tile_size, generator=generator)
            latents.append(noise)

        # 2. Get sigma schedule
        real_model = model.model
        sampler = comfy.samplers.KSampler(
            real_model, steps=steps, device=device,
            sampler=sampler_name, scheduler=scheduler,
            denoise=1.0,
        )
        sigmas = sampler.sigmas

        # 3. Precompute 3x3 neighbor maps for all 16 cases
        neighbor_maps = [get_3x3_neighbors(i) for i in range(16)]

        # 4. Denoise step by step
        for step_idx in range(len(sigmas) - 1):
            sigma = sigmas[step_idx]
            sigma_next = sigmas[step_idx + 1]

            new_latents = [None] * 16

            # Process each tile sequentially (VRAM budget)
            for tile_idx in range(16):
                neighbors = neighbor_maps[tile_idx]

                # Build 3x3 latent patch
                patch = torch.zeros(1, 4, tile_size * 3, tile_size * 3,
                                    device="cpu")
                for r in range(3):
                    for c in range(3):
                        nb_idx = neighbors[r][c]
                        patch[0, :,
                              r * tile_size:(r + 1) * tile_size,
                              c * tile_size:(c + 1) * tile_size] = latents[nb_idx][0]

                # Move to device
                patch = patch.to(device)
                sigma_batch = sigma.unsqueeze(0).to(device)

                # Apply SharedGroupNorm and run single step
                with patch_groupnorm(real_model.diffusion_model):
                    noise_pred = comfy.samplers.sampling_function(
                        model, patch, sigma_batch,
                        positive, negative, cfg,
                    )

                # Apply sigma step (Euler step)
                dt = sigma_next - sigma
                patch = patch + noise_pred * dt

                # Extract center tile
                center = patch[0, :,
                               tile_size:2 * tile_size,
                               tile_size:2 * tile_size].unsqueeze(0).cpu()
                new_latents[tile_idx] = center

                # Free VRAM
                del patch, noise_pred
                comfy.model_management.soft_empty_cache()

            latents = new_latents

        # 5. VAE decode all 16 tiles
        decoded_tiles = []
        for i in range(16):
            latent_sample = latents[i].to(device)
            pixels = vae.decode(latent_sample)
            decoded_tiles.append(pixels[0])  # [H, W, C]
            del latent_sample
            comfy.model_management.soft_empty_cache()

        return (torch.stack(decoded_tiles),)

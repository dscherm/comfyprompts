"""ComfyUI node for generating marching squares grayscale masks."""

import torch

from ..utils.marching_squares import MARCHING_SQUARES_CASES


class MarchingSquaresMasks:
    """Generates 16 grayscale masks for dual-terrain blending."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "width": ("INT", {"default": 512, "min": 64, "max": 2048}),
                "height": ("INT", {"default": 512, "min": 64, "max": 2048}),
                "gradient_width": ("FLOAT", {"default": 0.25, "min": 0.0, "max": 0.5, "step": 0.01}),
                "invert": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "generate"
    CATEGORY = "tileset"

    def generate(self, width, height, gradient_width, invert):
        # Normalized coordinates [0,1]
        y_coords = torch.linspace(0, 1, height).unsqueeze(1).expand(height, width)
        x_coords = torch.linspace(0, 1, width).unsqueeze(0).expand(height, width)

        masks = []
        for case in MARCHING_SQUARES_CASES:
            # Bilinear interpolation of corner values
            tl = float(case.top_left)
            tr = float(case.top_right)
            bl = float(case.bottom_left)
            br = float(case.bottom_right)

            # Bilinear: lerp corners
            top = tl * (1 - x_coords) + tr * x_coords
            bottom = bl * (1 - x_coords) + br * x_coords
            field = top * (1 - y_coords) + bottom * y_coords

            # Apply gradient: map [0.5 - gw, 0.5 + gw] -> [0, 1]
            if gradient_width > 0:
                mask = (field - (0.5 - gradient_width)) / (2 * gradient_width)
                mask = mask.clamp(0, 1)
            else:
                mask = (field >= 0.5).float()

            if invert:
                mask = 1.0 - mask

            masks.append(mask.unsqueeze(-1))  # [H, W, 1]

        # Stack to [16, H, W, 1]
        return (torch.stack(masks),)

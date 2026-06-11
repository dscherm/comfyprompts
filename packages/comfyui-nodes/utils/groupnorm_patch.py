"""SharedGroupNorm for cross-tile style consistency during non-manifold diffusion."""

from contextlib import contextmanager

import torch
import torch.nn as nn


class SharedGroupNorm(nn.Module):
    """GroupNorm variant that shares statistics across all samples in the batch.

    Standard GroupNorm computes mean/var per sample. SharedGroupNorm computes
    them across ALL samples, forcing consistent style across tiles.
    """

    def __init__(self, original_gn: nn.GroupNorm):
        super().__init__()
        self.num_groups = original_gn.num_groups
        self.num_channels = original_gn.num_channels
        self.eps = original_gn.eps
        self.weight = original_gn.weight
        self.bias = original_gn.bias

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, C, H, W = x.shape
        G = self.num_groups
        x = x.view(B, G, C // G, H, W)

        # Shared stats across ALL samples + spatial dims
        mean = x.mean(dim=(0, 2, 3, 4), keepdim=True)
        var = x.var(dim=(0, 2, 3, 4), keepdim=True)
        x = (x - mean) / (var + self.eps).sqrt()
        x = x.view(B, C, H, W)

        if self.weight is not None:
            x = x * self.weight.view(1, C, 1, 1) + self.bias.view(1, C, 1, 1)

        return x


def _replace_groupnorms(module: nn.Module) -> dict[str, nn.GroupNorm]:
    """Replace all GroupNorm layers with SharedGroupNorm, return originals."""
    originals = {}
    for name, child in list(module.named_modules()):
        if isinstance(child, nn.GroupNorm) and not isinstance(child, SharedGroupNorm):
            originals[name] = child
            # Navigate to parent module and replace
            parts = name.split(".")
            parent = module
            for part in parts[:-1]:
                parent = getattr(parent, part)
            setattr(parent, parts[-1], SharedGroupNorm(child))
    return originals


def _restore_groupnorms(module: nn.Module, originals: dict[str, nn.GroupNorm]):
    """Restore original GroupNorm layers."""
    for name, original in originals.items():
        parts = name.split(".")
        parent = module
        for part in parts[:-1]:
            parent = getattr(parent, part)
        setattr(parent, parts[-1], original)


@contextmanager
def patch_groupnorm(model: nn.Module):
    """Context manager that temporarily replaces GroupNorm with SharedGroupNorm.

    Usage:
        with patch_groupnorm(unet):
            output = unet(input_batch)
    """
    originals = _replace_groupnorms(model)
    try:
        yield model
    finally:
        _restore_groupnorms(model, originals)

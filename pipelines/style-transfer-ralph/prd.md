# Style Transfer — Requirements

## Overview

Style-transfer-ralph applies a consistent art style across a batch of images or assets using IP-Adapter, LoRA presets, and prompt engineering. It ensures every output in a batch matches the reference style, maintaining visual cohesion for game asset packs, marketing materials, or themed content sets.

## Target State

Given a style reference (image or LoRA preset) and a set of target images, the pipeline delivers styled versions of every target image with consistent application of the style. A style manifest documents the configuration used and per-image quality metrics.

## Acceptance Criteria

1. Style reference is captured as a reusable preset: LoRA name/weight, IP-Adapter strength, and prompt modifiers
2. All target images are processed through the same style pipeline with identical settings
3. Styled outputs maintain the compositional structure of their source images (subjects remain recognizable)
4. Color palette across all styled outputs is consistent with the style reference (mean color distance < threshold)
5. Style strength is uniform across the batch -- no image appears noticeably more or less stylized than others
6. Styled images maintain the original resolution of their source images
7. No generation artifacts: no obvious tiling, no color banding, no hallucinated elements foreign to the source
8. Caption analysis of styled outputs confirms style keywords are present (e.g., "watercolor", "pixel art", "oil painting")
9. Each styled image has a quality score computed via captioning that meets the minimum threshold
10. STYLE-MANIFEST.md documents: style name, reference image(s), LoRA/IP-Adapter settings, per-image scores, and export formats
11. Batch processing completes all images -- zero dropped targets
12. Pipeline completes within max_iterations (20) without manual intervention

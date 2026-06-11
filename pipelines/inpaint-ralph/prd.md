# Inpaint — Requirements

## Overview

Inpaint-ralph implements self-correcting image generation. Rather than accepting whatever the first generation produces, it iteratively evaluates the output against the original prompt using caption-based semantic analysis, identifies mismatches, and uses targeted inpainting to fix them until a quality threshold is met.

## Target State

Given a text prompt, the pipeline delivers a final image that faithfully represents the prompt intent. The self-correction loop (evaluate -> inpaint -> re-evaluate) runs until the semantic similarity score meets the threshold or the maximum loop count is reached. A generation report documents the full correction history.

## Acceptance Criteria

1. Initial image is generated at the requested resolution with the specified checkpoint and sampler settings
2. Evaluation stage produces a caption of the generated image and computes a semantic similarity score against the original prompt
3. Semantic similarity score is computed consistently (same prompt + image always produces the same score within tolerance)
4. Score threshold is configurable (default >= 0.8) and the pipeline stops refining once it is met
5. Each inpainting correction targets specific identified issues (not random regions) based on the evaluation diff
6. Score improves monotonically across correction loop iterations (each inpaint pass should not make things worse)
7. Maximum correction loops are respected (default: 5) to prevent infinite refinement
8. Final image maintains the original resolution and aspect ratio through all correction passes
9. No visible inpainting seams or artifacts at correction boundaries in the final image
10. GENERATION-REPORT.md documents: original prompt, checkpoint used, score after each loop iteration, issues identified and fixed, total iterations, and final score
11. All intermediate images (initial generation, each correction pass) are preserved in the output directory
12. Pipeline completes within max_iterations without manual intervention
13. If the score threshold cannot be met within max_loops, the pipeline exports the best-scoring image and reports the shortfall

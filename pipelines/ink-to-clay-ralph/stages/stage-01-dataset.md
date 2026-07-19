# Stage 1 — DATASET (bootstrap aligned ink↔clay pairs)

**Goal:** produce ~50–150 aligned `(ink, clay)` pairs for free, plus the clay-only
style set for Approach A. No GPU training here — this is generation via ComfyUI
(ComfyUI must be UP on the 3090 Ti; `ollama stop` first if it's holding VRAM).

## Do

1. Pick ~50–150 varied subjects: the 8 soapbox characters + generic props,
   creatures, and objects (for generalization). Write the subject list to
   `output/subjects.txt`.
2. For each subject, generate **the same subject at the same seed twice** with
   `soapbox_char_final_v1`:
   - **clay** → `mv_ortho`@0.85 + char@0.65, prompt: `mv_ortho, front view, full
     body, A/T-pose, <subject>, gritty_comic, plain flat neutral-grey background,
     orthographic, even lighting, no cast shadow`.
   - **ink** → char@0.9 (NO mv_ortho), prompt: `gritty_comic, <subject>, heavy
     black ink linework, cel shading, flat 2D comic illustration, white
     background`.
3. Save to `E:/ai-training/datasets/ink_to_clay_v1/{ink,clay}/<id>.png` with
   **matched filenames** (`<id>` identical across the two dirs).
4. Optionally supplement with any REAL ink drawings you own, each paired to a
   clay render you accept.
5. Build a curation **montage** (reuse `scripts/train_lora/build_montage.py`
   pattern: ink|clay side-by-side per row) and get **human approval** before
   Stage 2. Self-confirmation is not approval.

## Write an id-driven generator

Put a small script in `scripts/` (e.g. `bootstrap_pairs.py`) that reads
`subjects.txt`, drives the two generations per subject at a shared per-subject
seed, and writes the matched files. Reuse the toolchain's ComfyUI client /
`generate_image_lora` path; do not hardcode absolute output paths outside E:.

## Output artifacts
- `E:/ai-training/datasets/ink_to_clay_v1/ink/*.png`, `.../clay/*.png` (matched)
- `output/subjects.txt`, `output/pairs_montage.png`
- record counts + the seed policy in `pipeline-state.json` stage `1-dataset`.

→ Gate: `gates/gate-01-dataset.md`.

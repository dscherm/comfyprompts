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

## Generator — `scripts/bootstrap_pairs.py` (provided, tested dry-run)

Use the pre-built `scripts/bootstrap_pairs.py`: it drives ComfyUI over HTTP
(urllib only), builds a FLUX graph with **chained LoraLoaders** (clay =
mv_ortho@0.85 → char@0.65; ink = char@0.9), generates both styles per subject at
the **same seed**, and writes matched `{ink,clay}/<NNN_slug>.png`. It is
**resumable** (skips subjects whose pair already exists) and **keeps pairs
aligned** (drops a half-made pair on failure so the gate's match check holds).

```bash
# ComfyUI UP on the 3090 Ti (run_3090ti.ps1); `ollama stop` first if needed.
python scripts/bootstrap_pairs.py --dry-run          # sanity: builds workflows, no ComfyUI
python scripts/bootstrap_pairs.py --limit 3          # smoke: 3 subjects -> 6 images
python scripts/bootstrap_pairs.py                     # full default set (~48 subjects)
python scripts/bootstrap_pairs.py --subjects subs.txt # extend: one "slug: description" per line
```

Extend the built-in subject set toward the 50–150 the spec wants (add the real
soapbox character names + any real ink drawings you own) via `--subjects`.

## Output artifacts
- `E:/ai-training/datasets/ink_to_clay_v1/ink/*.png`, `.../clay/*.png` (matched)
- `output/subjects.txt`, `output/pairs_montage.png`
- record counts + the seed policy in `pipeline-state.json` stage `1-dataset`.

→ Gate: `gates/gate-01-dataset.md`.

# mv_ortho dataset manifest (M2)

**Location:** `E:\ai-training\datasets\mv_ortho\` (off-repo, like berserkr_style — avoids bloat)
**Trigger:** `mv_ortho` | **Total:** 125 images = 25 meshes × 5 views
**Rendered by:** `scripts/train_lora/render_multiview.py` via blender-mcp (orthographic,
neutral-grey bg, even 3-sun lighting, 768px).

## Selection principle — limb separation (the core requirement)

Only meshes already in a **wide T-pose with clearly separated limbs** (arms out with
visible gaps to the torso, legs apart) were included, so Hunyuan3D will produce
*separable* — not fused — geometry (cf. `project_mesh_intersection_fix`). This made
the clean rigged T-pose libraries the natural source.

## Views (front-weighted)

`front`, `front_left`, `front_right`, `left`, `right` — 3 of the 5 are front-facing,
matching the single-image-front objective. `back` was excluded (least useful for
Hunyuan3D front-input).

## Meshes included (25)

- **Mixamo mannequin (1):** `mixamo_xbot` — canonical clean wide T-pose, fingers spread.
- **Quaternius modmen (12):** adventurer, beach, casual, casual2, farmer, king, master,
  punk, spacesuit, suit, swat, worker.
- **Quaternius modwomen (11):** adventurer, casual, formal, master, medieval, punk,
  scifi, soldier, suit, witch, worker.
- **Project asset (1):** `wide_tpose_rookie_geom` — own wide-T-pose character (untextured
  geometry; lower contrast but canonical pose).

## Culled / excluded

- **Relaxed-pose characters** (arms down, hands near hips → fusion risk):
  `heimdall_watcher`, `player_textured`, and most `Hy3D_*`/`chargen_*` characters.
- **Non-characters:** all `*_kart_*`, cars, soapbox/soup_box (vehicles — this is a
  character LoRA).
- No meshes lost to the blank-render bug: Quaternius modwomen FBX bake Principled-BSDF
  `Alpha=0` (renders transparent in EEVEE); fixed in the renderer's `_force_opaque()`
  pass rather than culled, recovering ~60 images.

## Notes for downstream (M3/M4)

- This is a **pose/structure** dataset — predominantly stylized low-poly game characters
  in clean T-pose. `mv_ortho` therefore teaches separated-limb ortho framing; combine
  with a style prompt/LoRA at generation time for detailed concept art.
- Slight pose variance: a few (e.g. `modmen_master`) have arms angled below horizontal
  but limbs still clearly separated — acceptable.

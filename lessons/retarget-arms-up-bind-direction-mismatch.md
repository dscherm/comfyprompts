---
title: Mocap retarget forces arms up/frozen when source & target bind directions differ
severity: high
tags: [blender, rigging, retarget, animation]
source: hand-authored
created: 2026-06-30
project: comfyui-toolchain
---

## Symptom

A rest-pose-relative world-rotation mocap retarget produces a character whose
arms are pinned nearly straight up (`upperarm` world-Z ≈ +0.9) and barely move
across frames, regardless of the source clip. Legs look fine. Measuring the
source vs the retargeted bone shows the arms diverge hard (source upperarm
worldZ +0.25 → retargeted +0.92) while spine/hips/legs match.

## Root cause

The transfer applies the source bone's world rotation *delta-from-its-rest* onto
the TARGET bind: `target_dir(f) = delta · target_bind_dir`. That only equals the
source pose when `source_bind_dir == target_bind_dir`. When a bone's target bind
axis differs from the source's — notably the arms on a wide-T UniRig bind whose
roll/axis differs from the Mixamo/CMU source — the same world delta lands the arm
somewhere else. Legs survive only because their rest axes happen to align.

## Mitigation

1. Add a per-bone **bind-direction alignment**: before transfer, compute each
   bone's rest world DIRECTION for source and target (the bone's local +Y in
   world), and rotate the target's rest quaternion so it points the same way as
   the source's rest (`Quaternion = tgt_dir.rotation_difference(src_dir) @ tgt_rest`).
   Transfer the delta onto this aligned rest. Then `target_dir(f)` tracks
   `source_dir(f)`. It is a no-op where binds already align (legs).
2. Verify numerically, not just visually: sample upperarm/forearm world-Z on the
   source and the retargeted output at matching frames — they should match within
   ~0.05. A `+0.9` frozen reading is the signature of this bug.
3. Keep it default-on but switchable (a flag) so you can A/B against the legacy
   full-quaternion transfer.

## Notes (optional)

Once the retarget is faithful, a remaining "arms wrong" look is the SOURCE clip's
arm carriage (e.g. an alien/ROM take), not this bug — fix by clip curation, not
more alignment. Distinct from skin-weight distortion (see
unirig-skin-weights-melt-use-accurig): this lesson is about bone ROTATION, that
one is about mesh DEFORMATION.

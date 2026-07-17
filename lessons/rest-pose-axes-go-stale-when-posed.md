---
title: Rest-pose-measured axes/corrections go stale once the bone is posed far from rest
severity: high
tags: [rigging, blender, animation, quaternion, pose, measurement]
source: hand-authored
created: 2026-07-17
project: comfyui-toolchain
---

## Symptom

Three separate arm bugs in one session, all with ONE root cause:

- Meshy's forearms converged inward to meet at the centreline;
- the forearm rotated strangely, giving a snake / rubber-hose motion;
- the elbow bent sideways/inward instead of the forearm swinging forward.

Each was "fixed" by tuning, and each came back in a new form — the tell that
the cause was structural, not a parameter.

## Root cause

A rotation axis, or a neutral correction, MEASURED in the rig's rest pose
(a T-pose) was applied to a bone now posed far from rest (the arm hanging
~76 deg down). Two concrete failure modes:

1. **Stale hinge axis.** The elbow flex axis was measured (rest-bend cross
   product) with the arm horizontal. Applied to the hanging arm, that world
   axis is ~76 deg off, so "flexing the elbow" rotated the forearm in the wrong
   plane (frontal, inward) instead of the sagittal plane (forward).
2. **Rest-frame conjugation with a posed parent.** `local_from_world` conjugates
   a world rotation into a bone's LOCAL space using the bone's REST matrix
   (`bone.matrix_local`), which assumes the parent is at rest. Once the parent
   (upper arm) is posed by a large angle, the conjugation is wrong, and it
   compounded on rigs whose arms rest angled forward.

Knees and hips dodged all of this only because a leg barely rotates from its
rest orientation (both ~vertical), so rest-frame ≈ posed-frame there.

## Mitigation

1. **Derive orientation-dependent axes in the POSED frame, every frame**, not
   from the rest-pose manifest. Elbow flex: `flex_axis = current_upperarm_dir ×
   forward`, so the forearm always swings toward forward regardless of where the
   arm is in the cycle (and no stored fold sign is needed — geometry sets it).
2. **Set a bone's orientation via its posed WORLD matrix** (`pose_bone.matrix`,
   armature space) when the target is a world direction, instead of a rest-frame
   local quaternion. This is parent-agnostic: aim the bone's Y at the target,
   preserve the current 3x3 for roll, keep the head translation.
3. **Suspect this whenever a limb-END bug (forearm/hand/foot) survives multiple
   tuning passes and mutates.** The parent is posed far from rest; a rest-frame
   fact about the child is stale.

## Notes (optional)

Rest-frame facts that are safe to store and reuse: those on bones that stay near
their rest orientation (legs in a stand/walk). Related:
unirig-axis-conventions-transfer (axes that DO transfer, because they're
bone-local and the pose is mild), rig-vector-manifest-then-recipe (the manifest
stores rest-frame measurements — this lesson is the caveat on consuming them).

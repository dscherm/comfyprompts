"""MDM joints -> animated 'mocap' armature (Blender headless).

MDM emits 22-joint (SMPL/HumanML3D) world POSITIONS per frame in results.npy,
including the pelvis root translation (native forward motion). This builds a
Blender armature whose bones are named with the Mixamo `Character1_*` names that
`references/retarget_maps/mixamo_to_unirig.json` already targets — so the output
FBX feeds straight into the existing (root-motion-capable) retarget_mocap.py, no
new retarget math, no joints2bvh/IK/SMPL.

Per frame, each bone is aimed from its head joint toward its tail joint (a
positions->rotation solve); the hips also translate with the pelvis. The retarget
downstream is rest-pose-relative, so the exact roll/orientation convention here is
forgiving.

Usage (headless):
    blender --background --python mdm_to_source.py -- <results.npy> <out.fbx> [sample_idx]
"""
import bpy, sys, numpy as np
from mathutils import Vector, Matrix

a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
NPY, OUT = a[0], a[1]
SAMPLE = int(a[2]) if len(a) > 2 else 0

# SMPL/HumanML3D 22-joint indices:
# 0 pelvis 1 L_hip 2 R_hip 3 spine1 4 L_knee 5 R_knee 6 spine2 7 L_ankle 8 R_ankle
# 9 spine3 10 L_foot 11 R_foot 12 neck 13 L_collar 14 R_collar 15 head
# 16 L_sho 17 R_sho 18 L_elb 19 R_elb 20 L_wri 21 R_wri
# (name, head_joint, tail_joint, parent) -- names match mixamo_to_unirig.json keys.
BONES = [
    ("Character1_Hips",          0, 3, None),
    ("Character1_Spine",         3, 6, "Character1_Hips"),
    ("Character1_Spine1",        6, 9, "Character1_Spine"),
    ("Character1_Spine2",        9, 12, "Character1_Spine1"),
    ("Character1_Neck",          12, 15, "Character1_Spine2"),
    ("Character1_Head",          15, -1, "Character1_Neck"),      # -1 tail => synthesize
    ("Character1_LeftShoulder",  13, 16, "Character1_Spine2"),
    ("Character1_LeftArm",       16, 18, "Character1_LeftShoulder"),
    ("Character1_LeftForeArm",   18, 20, "Character1_LeftArm"),
    ("Character1_LeftHand",      20, -1, "Character1_LeftForeArm"),
    ("Character1_RightShoulder", 14, 17, "Character1_Spine2"),
    ("Character1_RightArm",      17, 19, "Character1_RightShoulder"),
    ("Character1_RightForeArm",  19, 21, "Character1_RightArm"),
    ("Character1_RightHand",     21, -1, "Character1_RightForeArm"),
    ("Character1_LeftUpLeg",     1, 4, "Character1_Hips"),
    ("Character1_LeftLeg",       4, 7, "Character1_LeftUpLeg"),
    ("Character1_LeftFoot",      7, 10, "Character1_LeftLeg"),
    ("Character1_RightUpLeg",    2, 5, "Character1_Hips"),
    ("Character1_RightLeg",      5, 8, "Character1_RightUpLeg"),
    ("Character1_RightFoot",     8, 11, "Character1_RightLeg"),
]
PARENT_JOINT = {b[1]: None for b in BONES}  # used only for synthesized tails


def load_joints(path, sample):
    """Return (T, 22, 3) float array in Blender Z-up coords."""
    d = np.load(path, allow_pickle=True).item()
    m = np.array(d["motion"])              # MDM: (n, 22, 3, T)
    s = m[sample]                          # (22, 3, T)
    s = np.transpose(s, (2, 0, 1))         # (T, 22, 3)
    # HumanML3D is Y-up; convert to Blender Z-up: (x,y,z) -> (x, -z, y)
    out = np.stack([s[..., 0], -s[..., 2], s[..., 1]], axis=-1)
    return out


def synth_tail(joints_f, head_j, parent_head_j):
    """Tail for leaf bones (head/hands): continue the parent->head direction."""
    h = Vector(joints_f[head_j])
    p = Vector(joints_f[parent_head_j])
    d = (h - p)
    if d.length < 1e-6:
        d = Vector((0, 0, 0.1))
    return h + d.normalized() * (d.length * 0.6)


def main():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
    J = load_joints(NPY, SAMPLE)           # (T,22,3)
    T = J.shape[0]
    rest = J[0]                            # rest from frame 0

    # leaf-bone tail source joints (parent head joint for direction)
    leaf_parent = {"Character1_Head": 12, "Character1_LeftHand": 18, "Character1_RightHand": 19}

    arm_data = bpy.data.armatures.new("MDM"); arm = bpy.data.objects.new("MDM", arm_data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm; arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = {}
    for name, hj, tj, parent in BONES:
        b = arm_data.edit_bones.new(name)
        head = Vector(rest[hj])
        tail = synth_tail(rest, hj, leaf_parent[name]) if tj < 0 else Vector(rest[tj])
        if (tail - head).length < 1e-4:
            tail = head + Vector((0, 0, 0.05))
        b.head = head; b.tail = tail; b.use_connect = False
        eb[name] = b
    for name, hj, tj, parent in BONES:
        if parent:
            eb[name].parent = eb[parent]
    bpy.ops.object.mode_set(mode='OBJECT')

    # rest world quats + dirs per bone
    restq, restdir = {}, {}
    for name, hj, tj, parent in BONES:
        bl = arm.matrix_world @ arm_data.bones[name].matrix_local
        restq[name] = bl.to_quaternion()
        h = Vector(rest[hj])
        t = synth_tail(rest, hj, leaf_parent[name]) if tj < 0 else Vector(rest[tj])
        restdir[name] = (t - h).normalized()

    # depth sort (parents first) so absolute world matrices compose correctly
    def depth(name):
        d, p = 0, dict((b[0], b[3]) for b in BONES)[name]
        while p:
            d += 1; p = dict((b[0], b[3]) for b in BONES)[p]
        return d
    order = sorted(BONES, key=lambda b: depth(b[0]))

    sc = bpy.context.scene
    sc.frame_start = 0; sc.frame_end = T - 1
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    for f in range(T):
        Jf = J[f]
        for name, hj, tj, parent in order:
            pb = arm.pose.bones[name]
            head = Vector(Jf[hj])
            tail = synth_tail(Jf, hj, leaf_parent[name]) if tj < 0 else Vector(Jf[tj])
            cur = (tail - head)
            cur = cur.normalized() if cur.length > 1e-6 else restdir[name]
            q = restdir[name].rotation_difference(cur) @ restq[name]
            pb.matrix = Matrix.Translation(head) @ q.to_matrix().to_4x4()
            bpy.context.view_layer.update()
            pb.keyframe_insert("rotation_quaternion", frame=f)
            if name == "Character1_Hips":
                pb.keyframe_insert("location", frame=f)

    for o in bpy.data.objects:
        o.select_set(o.type == 'ARMATURE')
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.fbx(filepath=OUT, use_selection=True, bake_anim=True,
                             add_leaf_bones=False, object_types={'ARMATURE'})
    print(f"MDM_SOURCE_DONE frames={T} bones={len(BONES)} -> {OUT}")


main()

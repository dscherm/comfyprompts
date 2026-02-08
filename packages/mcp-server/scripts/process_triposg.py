"""Process TripoSG model: fix weights, animate, export."""

import os

import bpy
import bmesh
from mathutils import Vector
import math

print('=== Step 1: Setup ===')

# Find mesh and rig
mesh = None
for obj in bpy.data.objects:
    if obj.type == 'MESH' and 'WGT' not in obj.name:
        mesh = obj
        break

rig = bpy.data.objects.get('RIG-Humanoid_Rig')
print(f'Mesh: {mesh.name} ({len(mesh.data.vertices)} verts)')
print(f'Rig: {rig.name}')

# Fix armature modifier
for mod in mesh.modifiers:
    if mod.type == 'ARMATURE':
        if mod.object != rig:
            print(f'Fixing modifier: {mod.object.name if mod.object else None} -> {rig.name}')
            mod.object = rig

# Check if weights exist with DEF- prefix
has_def_weights = False
for vg in mesh.vertex_groups:
    if vg.name.startswith('DEF-'):
        has_def_weights = True
        break

if not has_def_weights:
    print('\n=== Step 2: Assigning weights by proximity ===')

    # Clear and recreate vertex groups
    mesh.vertex_groups.clear()

    def_bones = [b for b in rig.data.bones if b.name.startswith('DEF-')]
    print(f'Creating {len(def_bones)} vertex groups...')

    for bone in def_bones:
        mesh.vertex_groups.new(name=bone.name)

    # Assign weights
    bm = bmesh.new()
    bm.from_mesh(mesh.data)
    bm.verts.ensure_lookup_table()
    deform_layer = bm.verts.layers.deform.verify()

    total_verts = len(bm.verts)
    print(f'Processing {total_verts} vertices...')

    for idx, v in enumerate(bm.verts):
        if idx % 100000 == 0:
            print(f'  Progress: {idx}/{total_verts}')

        v_world = mesh.matrix_world @ v.co

        bone_distances = []
        for bone in def_bones:
            head = rig.matrix_world @ bone.head_local
            tail = rig.matrix_world @ bone.tail_local
            bone_vec = tail - head
            bone_len = bone_vec.length

            if bone_len < 0.001:
                dist = (v_world - head).length
            else:
                bone_dir = bone_vec / bone_len
                t = max(0, min(1, (v_world - head).dot(bone_dir) / bone_len))
                closest = head + bone_dir * (t * bone_len)
                dist = (v_world - closest).length

            bone_distances.append((bone.name, dist))

        bone_distances.sort(key=lambda x: x[1])

        weights = []
        total = 0
        for name, dist in bone_distances[:4]:
            w = 1.0 / max(0.001, dist * dist)
            weights.append((name, w))
            total += w

        if total > 0:
            for name, w in weights:
                vg = mesh.vertex_groups.get(name)
                if vg:
                    v[deform_layer][vg.index] = w / total

    bm.to_mesh(mesh.data)
    bm.free()
    print('Weights assigned!')
else:
    print('DEF- weights already exist, skipping weight assignment...')

print('\n=== Step 3: Applying walk animation ===')

DURATION = 1.0
FPS = 30
INTENSITY = 1.0


class RigBones:
    def __init__(self, armature):
        self.bones = armature.pose.bones
        self._cache = {}

    def find(self, role):
        if role in self._cache:
            return self._cache[role]

        patterns = {
            'hips': ['hips', 'hip', 'pelvis', 'torso'],
            'spine': ['spine_fk', 'spine', 'DEF-spine'],
            'spine_upper': ['spine_fk.001', 'chest', 'DEF-spine.001'],
            'head': ['head', 'DEF-head'],
            'thigh_l': ['thigh_fk.L', 'thigh.L', 'DEF-thigh.L'],
            'thigh_r': ['thigh_fk.R', 'thigh.R', 'DEF-thigh.R'],
            'shin_l': ['shin_fk.L', 'shin.L', 'DEF-shin.L'],
            'shin_r': ['shin_fk.R', 'shin.R', 'DEF-shin.R'],
            'foot_l': ['foot_fk.L', 'foot.L', 'DEF-foot.L'],
            'foot_r': ['foot_fk.R', 'foot.R', 'DEF-foot.R'],
            'upper_arm_l': ['upper_arm_fk.L', 'DEF-upper_arm.L'],
            'upper_arm_r': ['upper_arm_fk.R', 'DEF-upper_arm.R'],
            'forearm_l': ['forearm_fk.L', 'DEF-forearm.L'],
            'forearm_r': ['forearm_fk.R', 'DEF-forearm.R'],
            'shoulder_l': ['shoulder.L', 'DEF-shoulder.L'],
            'shoulder_r': ['shoulder.R', 'DEF-shoulder.R'],
        }

        if role not in patterns:
            return None

        for pattern in patterns[role]:
            for bone in self.bones:
                if pattern.lower() == bone.name.lower():
                    self._cache[role] = bone
                    return bone

        for pattern in patterns[role]:
            for bone in self.bones:
                if pattern.lower() in bone.name.lower():
                    self._cache[role] = bone
                    return bone
        return None


def set_keyframe(bone, frame, location=None, rotation=None):
    if location:
        bone.location = location
        bone.keyframe_insert(data_path='location', frame=frame)
    if rotation:
        bone.rotation_mode = 'XYZ'
        bone.rotation_euler = rotation
        bone.keyframe_insert(data_path='rotation_euler', frame=frame)


action_name = f'{rig.name}_walk'
action = bpy.data.actions.new(name=action_name)
rig.animation_data_create()
rig.animation_data.action = action

rb = RigBones(rig)
num_frames = int(DURATION * FPS)
animated = []

for i in range(num_frames):
    t = i / (num_frames - 1)
    frame = i + 1
    phase = t * 2 * math.pi
    half = phase * 2

    hips = rb.find('hips')
    if hips:
        set_keyframe(hips, frame,
            location=(math.sin(phase) * 0.025, 0, -abs(math.sin(half)) * 0.015),
            rotation=(math.sin(half) * 0.02, 0, math.sin(phase) * 0.03))
        if 'hips' not in animated:
            animated.append('hips')

    spine = rb.find('spine')
    if spine:
        set_keyframe(spine, frame, rotation=(0.02, math.sin(phase) * 0.03, 0))
        if 'spine' not in animated:
            animated.append('spine')

    head = rb.find('head')
    if head:
        set_keyframe(head, frame, rotation=(math.sin(half) * 0.015, 0, 0))
        if 'head' not in animated:
            animated.append('head')

    for side, sign in [('_l', 1), ('_r', -1)]:
        thigh = rb.find(f'thigh{side}')
        if thigh:
            set_keyframe(thigh, frame, rotation=(sign * math.sin(phase) * 0.38, 0, 0))
            if f'thigh{side}' not in animated:
                animated.append(f'thigh{side}')

        shin = rb.find(f'shin{side}')
        if shin:
            bend = max(0, sign * math.sin(phase - 0.5)) * 0.45
            set_keyframe(shin, frame, rotation=(bend, 0, 0))
            if f'shin{side}' not in animated:
                animated.append(f'shin{side}')

        foot = rb.find(f'foot{side}')
        if foot:
            set_keyframe(foot, frame, rotation=(-sign * math.sin(phase) * 0.2, 0, 0))
            if f'foot{side}' not in animated:
                animated.append(f'foot{side}')

        arm = rb.find(f'upper_arm{side}')
        if arm:
            set_keyframe(arm, frame, rotation=(-sign * math.sin(phase) * 0.35, 0.1 * sign, 0))
            if f'upper_arm{side}' not in animated:
                animated.append(f'upper_arm{side}')

        forearm = rb.find(f'forearm{side}')
        if forearm:
            bend = 0.3 + max(0, -sign * math.sin(phase)) * 0.2
            set_keyframe(forearm, frame, rotation=(bend, 0, 0))
            if f'forearm{side}' not in animated:
                animated.append(f'forearm{side}')

bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = num_frames

print(f'Animation applied to {len(animated)} bones: {animated}')

print('\n=== Step 4: Saving and Exporting ===')
bpy.ops.wm.save_mainfile()

bpy.ops.object.select_all(action='DESELECT')
mesh.select_set(True)
rig.select_set(True)

output_glb = os.path.join(os.path.dirname(bpy.data.filepath) or os.getcwd(), 'triposg_animated.glb')
bpy.ops.export_scene.gltf(
    filepath=output_glb,
    export_format='GLB',
    export_animations=True,
    export_skins=True,
    use_selection=True,
    export_def_bones=True
)
print(f'Exported to: {output_glb}')
print('\nDone!')

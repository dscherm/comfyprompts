"""
Proximity-based vertex weight assignment for UniRig skeletons.
For each vertex, finds the N nearest bones and assigns smooth weights
based on distance. More reliable than bone heat for point-cloud meshes.
"""
import bpy
from mathutils import Vector
import math


def get_bone_segments(armature):
    """Get world-space head/tail positions for each bone."""
    segments = {}
    for bone in armature.data.bones:
        head = armature.matrix_world @ bone.head_local
        tail = armature.matrix_world @ bone.tail_local
        segments[bone.name] = (head, tail)
    return segments


def point_to_segment_dist(p, a, b):
    """Distance from point p to line segment a-b."""
    ab = b - a
    ap = p - a
    ab_len_sq = ab.length_squared
    if ab_len_sq < 1e-8:
        return (p - a).length
    t = max(0, min(1, ap.dot(ab) / ab_len_sq))
    closest = a + t * ab
    return (p - closest).length


def assign_proximity_weights(mesh_obj, armature, max_bones=4, falloff=2.0):
    """Assign vertex weights based on proximity to nearest bones."""
    segments = get_bone_segments(armature)
    bone_names = list(segments.keys())

    # Create vertex groups for all bones
    mesh_obj.vertex_groups.clear()
    for name in bone_names:
        mesh_obj.vertex_groups.new(name=name)

    weighted = 0
    for v in mesh_obj.data.vertices:
        wco = mesh_obj.matrix_world @ v.co

        # Calculate distance to each bone segment
        dists = []
        for name in bone_names:
            head, tail = segments[name]
            d = point_to_segment_dist(wco, head, tail)
            dists.append((name, d))

        # Sort by distance, take nearest N
        dists.sort(key=lambda x: x[1])
        nearest = dists[:max_bones]

        # Skip if all distances are huge (shouldn't happen)
        if not nearest or nearest[0][1] > 10.0:
            continue

        # Convert distances to weights with falloff
        # w = 1 / (d^falloff + epsilon)
        raw_weights = []
        for name, d in nearest:
            w = 1.0 / (d ** falloff + 0.001)
            raw_weights.append((name, w))

        # Normalize
        total = sum(w for _, w in raw_weights)
        if total < 1e-8:
            continue

        for name, w in raw_weights:
            normalized = w / total
            if normalized > 0.01:
                vg = mesh_obj.vertex_groups[name]
                vg.add([v.index], normalized, 'REPLACE')

        weighted += 1

    return weighted


def main():
    armature = None
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            armature = obj
            break

    if not armature:
        print("ERROR: No armature")
        return

    meshes = [o for o in bpy.data.objects if o.type == 'MESH' and len(o.data.vertices) > 50]

    for mesh_obj in meshes:
        # Clear existing
        mesh_obj.vertex_groups.clear()
        for mod in list(mesh_obj.modifiers):
            if mod.type == 'ARMATURE':
                mesh_obj.modifiers.remove(mod)
        mesh_obj.parent = None

        # Assign proximity weights
        weighted = assign_proximity_weights(mesh_obj, armature, max_bones=4, falloff=2.0)

        # Parent to armature and add modifier
        mesh_obj.parent = armature
        arm_mod = mesh_obj.modifiers.new("Armature", "ARMATURE")
        arm_mod.object = armature

        pct = weighted / len(mesh_obj.data.vertices) * 100
        print(f"{mesh_obj.name}: {weighted}/{len(mesh_obj.data.vertices)} ({pct:.0f}%) weighted")

    print("PROXIMITY_WEIGHTS_DONE")


if __name__ == "__main__":
    main()

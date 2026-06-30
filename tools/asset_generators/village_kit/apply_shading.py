"""Apply vertex-color gradient shading to ALL kit GLBs (post-process, no rebuild),
swap in the 6 improved pieces. Overwrites kit_glb/ + kit2_glb/ in place.
blender -b --python apply_shading.py"""
import bpy, math, os, glob, random, shutil
D="C:/Users/scher/AppData/Local/Temp/claude/D--Projects-comfyui-toolchain/25899eda-2041-4e64-a0a8-0c83c9100526/scratchpad"
G1=f"{D}/kit_glb"; G2=f"{D}/kit2_glb"; IMP=f"{D}/kit_improved_glb"
WIN=Hx_win=(1.0,0.81,0.29)  # window glow color

def make_mats():
    vc=bpy.data.materials.new("kit_vcol"); vc.use_nodes=True
    b=vc.node_tree.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value=0.9
    n=vc.node_tree.nodes.new("ShaderNodeVertexColor"); n.layer_name="Col"
    vc.node_tree.links.new(n.outputs["Color"], b.inputs["Base Color"])
    gm=bpy.data.materials.new("kit_glow"); gm.use_nodes=True
    g=gm.node_tree.nodes["Principled BSDF"]; g.inputs["Emission Color"].default_value=(*WIN,1)
    g.inputs["Emission Strength"].default_value=1.8; g.inputs["Base Color"].default_value=(*WIN,1)
    return vc,gm

def shade(name, src, out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    VCOL,GLOWM=make_mats()
    bpy.ops.import_scene.gltf(filepath=src)
    meshes=[o for o in bpy.data.objects if o.type=='MESH']
    rnd=random.Random(hash(name)&0xffff)
    for o in meshes:
        me=o.data
        bcols=[]; emis=[]
        for ms in me.materials:
            bc=(0.5,0.5,0.5); es=False
            if ms and ms.use_nodes:
                bsdf=ms.node_tree.nodes.get("Principled BSDF")
                if bsdf:
                    c=bsdf.inputs["Base Color"].default_value; bc=(c[0],c[1],c[2])
                    es=bsdf.inputs["Emission Strength"].default_value>0.01
            bcols.append(bc); emis.append(es)
        if not bcols: bcols=[(0.5,0.5,0.5)]; emis=[False]
        poly_em=[emis[p.material_index] if p.material_index<len(emis) else False for p in me.polygons]
        zs=[(o.matrix_world@v.co).z for v in me.vertices]; minz=min(zs); span=max(max(zs)-minz,1e-4)
        ca=me.color_attributes.new(name="Col",type='BYTE_COLOR',domain='CORNER')
        for poly in me.polygons:
            base=bcols[poly.material_index] if poly.material_index<len(bcols) else (0.5,0.5,0.5)
            fn=1.0+(rnd.random()-0.5)*0.07
            for li in poly.loop_indices:
                z=(o.matrix_world@me.vertices[me.loops[li].vertex_index].co).z
                t=(z-minz)/span; f=(0.72+0.52*t)*fn
                ca.data[li].color=(min(base[0]*f,1),min(base[1]*f,1),min(base[2]*f,1),1.0)
        me.materials.clear(); me.materials.append(VCOL); me.materials.append(GLOWM)
        for i,poly in enumerate(me.polygons): poly.material_index=1 if poly_em[i] else 0
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=out,export_format='GLB',use_selection=True)

IMPROVED={"windmill","stone_bridge","church","tree_dead"}  # use already-shaded improved GLBs
V1=["cottage","house_small","house_tall","tavern","church","barn","tower","blacksmith","wall","wall_gate",
 "wall_corner","ground_grass","ground_dirt","path_straight","path_corner","well","market_stall","barrel",
 "crate","fence","tree","tree_dead","lamppost","brazier","signpost","cart","haystack","gravestone"]
V2=["windmill","ruined_house","stable","guard_tower","stone_bridge","portcullis","wall_ruined","palisade",
 "fountain","wood_pile","torch","banner","stocks","anvil","trough","weapon_rack","gibbet","bone_pile",
 "crypt","pine","stump","rocks","bush"]
n=0
for name in V1:
    if name in IMPROVED: shutil.copy(f"{IMP}/{name}.glb", f"{G1}/{name}.glb")
    else: shade(name, f"{G1}/{name}.glb", f"{G1}/{name}.glb")
    n+=1
for name in V2:
    if name in IMPROVED: shutil.copy(f"{IMP}/{name}.glb", f"{G2}/{name}.glb")
    else: shade(name, f"{G2}/{name}.glb", f"{G2}/{name}.glb")
    n+=1
# new pieces from improved set
shutil.copy(f"{IMP}/gate_arch.glb", f"{G2}/gate_arch.glb")
shutil.copy(f"{IMP}/graveyard.glb", f"{G2}/graveyard.glb")
print(f"SHADED {n} pieces + 2 new (gate_arch, graveyard)")
